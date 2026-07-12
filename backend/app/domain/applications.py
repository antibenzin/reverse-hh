"""Application state machine and business logic (ADR-0003)."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.domain.access import NotMemberError, require_membership
from app.domain.notifications import (
    notify_application_accepted,
    notify_application_rejected,
    notify_application_submitted,
)
from app.domain.resume_visibility import is_resume_hidden_from_company
from app.domain.resumes import build_published_payload, load_resume
from app.domain.tests import test_to_response
from app.models import (
    Application,
    ApplicationTestAnswer,
    CandidateProfile,
    Chat,
    Company,
    Resume,
    ResumeTest,
    User,
    Vacancy,
)
from app.models.enums import ApplicationStatus, ResumeStatus, VacancyStatus

APPLICATION_STATUSES = frozenset(ApplicationStatus)

Actor = Literal["employer", "candidate", "system"]

DEFAULT_EXPIRY_DAYS = 14

TRANSITIONS: dict[tuple[ApplicationStatus, ApplicationStatus], frozenset[Actor]] = {
    (ApplicationStatus.SENT, ApplicationStatus.VIEWED): frozenset({"candidate"}),
    (ApplicationStatus.SENT, ApplicationStatus.EXPIRED): frozenset({"system"}),
    (ApplicationStatus.VIEWED, ApplicationStatus.ACCEPTED): frozenset({"candidate"}),
    (ApplicationStatus.VIEWED, ApplicationStatus.REJECTED): frozenset({"candidate"}),
    (ApplicationStatus.VIEWED, ApplicationStatus.EXPIRED): frozenset({"system"}),
    (ApplicationStatus.ACCEPTED, ApplicationStatus.CLOSED_AFTER_ACCEPTANCE): frozenset(
        {"candidate"}
    ),
    (ApplicationStatus.EXPIRED, ApplicationStatus.REACTIVATION_REQUESTED): frozenset(
        {"candidate"}
    ),
    (ApplicationStatus.REACTIVATION_REQUESTED, ApplicationStatus.REACTIVATED): frozenset(
        {"employer"}
    ),
    (ApplicationStatus.REACTIVATION_REQUESTED, ApplicationStatus.EXPIRED): frozenset(
        {"employer", "system"}
    ),
    (ApplicationStatus.REACTIVATED, ApplicationStatus.VIEWED): frozenset({"candidate"}),
    (ApplicationStatus.REACTIVATED, ApplicationStatus.ACCEPTED): frozenset({"candidate"}),
    (ApplicationStatus.REACTIVATED, ApplicationStatus.REJECTED): frozenset({"candidate"}),
    (ApplicationStatus.REACTIVATED, ApplicationStatus.EXPIRED): frozenset({"system"}),
}


class InvalidTransitionError(Exception):
    pass


class ApplicationNotFoundError(Exception):
    pass


class ApplicationAccessDeniedError(Exception):
    pass


class DuplicateApplicationError(Exception):
    pass


class ApplicationValidationError(Exception):
    pass


class LimitExceededError(Exception):
    pass


class AutoRejectConfirmationRequiredError(Exception):
    def __init__(self, warnings: list[str]):
        self.warnings = warnings
        super().__init__("Auto-reject confirmation required")


@dataclass(frozen=True)
class TestAnswerInput:
    question_id: uuid.UUID
    text: str | None = None
    option_ids: list[uuid.UUID] | None = None
    scale: int | None = None


@dataclass(frozen=True)
class CanApplyResult:
    can_apply: bool
    warnings: list[str]
    test_required: bool


def _now() -> datetime:
    return datetime.now(UTC)


def _load_application(db: Session, application_id: uuid.UUID) -> Application | None:
    return (
        db.query(Application)
        .options(
            joinedload(Application.resume).joinedload(Resume.candidate_profile),
            joinedload(Application.chat),
            joinedload(Application.test_answers),
        )
        .filter(Application.id == application_id)
        .first()
    )


def _assert_transition(
    application: Application, to_status: ApplicationStatus, actor: Actor
) -> None:
    key = (application.status, to_status)
    allowed_actors = TRANSITIONS.get(key)
    if not allowed_actors or actor not in allowed_actors:
        raise InvalidTransitionError(
            f"Cannot transition from {application.status.value} to {to_status.value}"
        )


def _debit_limit(company: Company) -> None:
    if company.application_limit_monthly == 0:
        return
    if company.applications_used_this_month >= company.application_limit_monthly:
        raise LimitExceededError()
    company.applications_used_this_month += 1


def compute_mismatch_flags(resume_data: dict, vacancy_data: dict) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    resume_min = resume_data.get("salary_min")
    vacancy_max = vacancy_data.get("salary_max") or vacancy_data.get("salary_fixed")
    if resume_min is not None and vacancy_max is not None:
        flags["salary"] = vacancy_max < resume_min
    else:
        flags["salary"] = False

    resume_formats = set(resume_data.get("work_formats") or [])
    vacancy_format = vacancy_data.get("work_format")
    flags["work_format"] = bool(
        resume_formats and vacancy_format and vacancy_format not in resume_formats
    )

    resume_city = (resume_data.get("city") or "").lower()
    vacancy_city = (vacancy_data.get("city") or "").lower()
    flags["location"] = bool(resume_city and vacancy_city and resume_city != vacancy_city)
    return flags


def _auto_reject_mode(settings: dict | None, key: str) -> str | None:
    if not settings:
        return None
    rule = settings.get(key) or {}
    if not rule.get("enabled"):
        return None
    return rule.get("mode")


def _build_warnings(flags: dict[str, bool], settings: dict | None) -> list[str]:
    warnings: list[str] = []
    if flags.get("salary"):
        warnings.append("salary_mismatch")
    if flags.get("work_format"):
        warnings.append("work_format_mismatch")
    if flags.get("location"):
        warnings.append("location_mismatch")
    if any(
        flags.get(key) and _auto_reject_mode(settings, key) == "auto_reject"
        for key in ("salary", "work_format", "location")
    ):
        warnings.append("auto_reject_risk")
    return warnings


def _should_force_auto_reject(
    flags: dict[str, bool], settings: dict | None, *, confirm: bool
) -> bool:
    for key in ("salary", "work_format", "location"):
        if flags.get(key) and _auto_reject_mode(settings, key) == "auto_reject":
            if not confirm:
                raise AutoRejectConfirmationRequiredError(_build_warnings(flags, settings))
            return True
    return False


def _resume_accessible_to_company(resume: Resume, company: Company) -> bool:
    if is_resume_hidden_from_company(resume, company):
        return False
    if resume.status != ResumeStatus.PUBLISHED or resume.test_editing:
        return False
    if resume.visibility.value in ("public", "link_only"):
        return True
    return False


def _build_resume_snapshot(resume: Resume) -> dict[str, Any]:
    return build_published_payload(resume, mask_nda=True)


def _build_vacancy_snapshot(vacancy: Vacancy) -> dict[str, Any]:
    data = copy.deepcopy(vacancy.data or {})
    data["vacancy_id"] = str(vacancy.id)
    data["status"] = vacancy.status.value
    return data


def _build_test_snapshot(test: ResumeTest | None) -> dict[str, Any] | None:
    if not test or not test.is_published:
        return None
    return test_to_response(test, hide_scoring=True)


def _validate_test_answers(
    test: ResumeTest | None, answers: list[TestAnswerInput] | None
) -> None:
    if not test or not test.is_published:
        return
    if not answers:
        raise ApplicationValidationError("Test answers are required")
    question_ids = {q.id for q in test.questions}
    answered = {a.question_id for a in answers}
    if question_ids != answered:
        raise ApplicationValidationError("All test questions must be answered")


def _validate_cover_letter(resume: Resume, cover_letter: str | None) -> None:
    if not resume.cover_letter_required:
        return
    if not cover_letter or len(cover_letter) < 300 or len(cover_letter) > 3000:
        raise ApplicationValidationError("Cover letter must be 300-3000 characters")


def can_apply(
    db: Session,
    *,
    company: Company,
    resume: Resume,
    vacancy: Vacancy,
) -> CanApplyResult:
    warnings: list[str] = []
    if vacancy.company_id != company.id:
        return CanApplyResult(
            can_apply=False, warnings=["vacancy_company_mismatch"], test_required=False
        )
    if vacancy.status != VacancyStatus.ACTIVE:
        return CanApplyResult(
            can_apply=False, warnings=["vacancy_not_active"], test_required=False
        )
    if not _resume_accessible_to_company(resume, company):
        return CanApplyResult(
            can_apply=False, warnings=["resume_not_accessible"], test_required=False
        )
    resume_data = resume.published_data or {}
    vacancy_data = vacancy.data or {}
    flags = compute_mismatch_flags(resume_data, vacancy_data)
    warnings.extend(_build_warnings(flags, resume.auto_reject_settings))
    test_required = bool(resume.test and resume.test.is_published)
    return CanApplyResult(can_apply=True, warnings=warnings, test_required=test_required)


def application_to_response(
    application: Application, *, company_moderation_warning: bool | None = None
) -> dict[str, Any]:
    resume_data = application.resume_snapshot or {}
    mismatch_flags = resume_data.get("__mismatch_flags", {})
    payload = {
        "id": str(application.id),
        "status": application.status.value,
        "resume_snapshot": {k: v for k, v in resume_data.items() if k != "__mismatch_flags"},
        "vacancy_snapshot": application.vacancy_snapshot,
        "cover_letter": application.cover_letter,
        "mismatch_flags": mismatch_flags,
        "expires_at": application.expires_at.isoformat(),
        "created_at": application.created_at.isoformat(),
    }
    if company_moderation_warning is not None:
        payload["company_moderation_warning"] = company_moderation_warning
    return payload


def _candidate_owns_application(db: Session, user: User, application: Application) -> bool:
    profile = (
        db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    )
    if not profile:
        return False
    return application.resume.candidate_profile_id == profile.id


def get_application_for_user(db: Session, *, user: User, application_id: uuid.UUID) -> Application:
    application = _load_application(db, application_id)
    if not application:
        raise ApplicationNotFoundError()
    if _candidate_owns_application(db, user, application):
        return application
    membership = (
        db.query(Company)
        .filter(Company.id == application.company_id)
        .first()
    )
    if membership:
        try:
            require_membership(db, user=user, company_id=application.company_id)
            return application
        except NotMemberError:
            pass
    raise ApplicationAccessDeniedError()


def list_applications(
    db: Session,
    *,
    user: User,
    role: str,
    company_id: uuid.UUID | None = None,
) -> list[Application]:
    if role == "candidate":
        profile = (
            db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
        )
        if not profile:
            return []
        return (
            db.query(Application)
            .join(Resume)
            .filter(Resume.candidate_profile_id == profile.id)
            .order_by(Application.created_at.desc())
            .all()
        )
    if role == "employer":
        if not company_id:
            raise ApplicationValidationError("X-Company-Id required for employer list")
        require_membership(db, user=user, company_id=company_id)
        return (
            db.query(Application)
            .filter(Application.company_id == company_id)
            .order_by(Application.created_at.desc())
            .all()
        )
    raise ApplicationValidationError("Invalid role")


def submit_application(
    db: Session,
    *,
    user: User,
    company_id: uuid.UUID,
    resume_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    cover_letter: str | None = None,
    test_answers: list[TestAnswerInput] | None = None,
    confirm_auto_reject_risk: bool = False,
) -> Application:
    require_membership(db, user=user, company_id=company_id)
    company = db.get(Company, company_id)
    if not company:
        raise ApplicationValidationError("Company not found")

    resume = load_resume(db, resume_id)
    vacancy = (
        db.query(Vacancy)
        .options(joinedload(Vacancy.recruiters))
        .filter(Vacancy.id == vacancy_id, Vacancy.company_id == company_id)
        .first()
    )
    if not resume or not vacancy:
        raise ApplicationValidationError("Resume or vacancy not found")

    check = can_apply(db, company=company, resume=resume, vacancy=vacancy)
    if not check.can_apply:
        raise ApplicationValidationError(check.warnings[0] if check.warnings else "Cannot apply")

    _validate_cover_letter(resume, cover_letter)
    _validate_test_answers(resume.test, test_answers)

    resume_data = resume.published_data or {}
    vacancy_data = vacancy.data or {}
    flags = compute_mismatch_flags(resume_data, vacancy_data)
    force_auto_reject = _should_force_auto_reject(
        flags, resume.auto_reject_settings, confirm=confirm_auto_reject_risk
    )

    resume_snapshot = _build_resume_snapshot(resume)
    resume_snapshot["__mismatch_flags"] = flags
    vacancy_snapshot = _build_vacancy_snapshot(vacancy)
    test_snapshot = _build_test_snapshot(resume.test)

    status = (
        ApplicationStatus.AUTO_REJECTED
        if force_auto_reject
        else ApplicationStatus.SENT
    )
    expires_at = _now() + timedelta(days=DEFAULT_EXPIRY_DAYS)

    application = Application(
        resume_id=resume_id,
        vacancy_id=vacancy_id,
        company_id=company_id,
        sent_by=user.id,
        status=status,
        resume_snapshot=resume_snapshot,
        vacancy_snapshot=vacancy_snapshot,
        test_snapshot=test_snapshot,
        cover_letter=cover_letter,
        expires_at=expires_at,
        limit_debited=False,
    )
    db.add(application)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise DuplicateApplicationError() from None

    _debit_limit(company)
    application.limit_debited = True

    if test_answers:
        for answer in test_answers:
            db.add(
                ApplicationTestAnswer(
                    application_id=application.id,
                    question_id=answer.question_id,
                    answer_text=answer.text,
                    answer_options=answer.option_ids,
                    answer_scale=answer.scale,
                )
            )

    application = _load_application(db, application.id) or application
    notify_application_submitted(db, application)
    db.commit()
    return application


def transition_application(
    db: Session,
    *,
    application: Application,
    to_status: ApplicationStatus,
    actor: Actor,
) -> Application:
    _assert_transition(application, to_status, actor)
    application.status = to_status
    if to_status == ApplicationStatus.VIEWED and application.viewed_at is None:
        application.viewed_at = _now()
    if to_status == ApplicationStatus.ACCEPTED:
        if not application.chat:
            db.add(Chat(application_id=application.id, is_read_only=False))
    if to_status == ApplicationStatus.CLOSED_AFTER_ACCEPTANCE and application.chat:
        application.chat.is_read_only = True
    if to_status == ApplicationStatus.REACTIVATED:
        application.expires_at = _now() + timedelta(days=DEFAULT_EXPIRY_DAYS)
    db.commit()
    return _load_application(db, application.id) or application


def mark_viewed(db: Session, *, user: User, application_id: uuid.UUID) -> Application:
    application = get_application_for_user(db, user=user, application_id=application_id)
    if not _candidate_owns_application(db, user, application):
        raise ApplicationAccessDeniedError()
    return transition_application(
        db, application=application, to_status=ApplicationStatus.VIEWED, actor="candidate"
    )


def accept_application(db: Session, *, user: User, application_id: uuid.UUID) -> Application:
    application = get_application_for_user(db, user=user, application_id=application_id)
    if not _candidate_owns_application(db, user, application):
        raise ApplicationAccessDeniedError()
    if application.status == ApplicationStatus.SENT:
        application = transition_application(
            db, application=application, to_status=ApplicationStatus.VIEWED, actor="candidate"
        )
    application = transition_application(
        db, application=application, to_status=ApplicationStatus.ACCEPTED, actor="candidate"
    )
    application = _load_application(db, application.id) or application
    notify_application_accepted(db, application)
    db.commit()
    return application


def reject_application(
    db: Session,
    *,
    user: User,
    application_id: uuid.UUID,
    reasons: list[str] | None = None,
    other_text: str | None = None,
    share_with_employer: bool = False,
) -> Application:
    application = get_application_for_user(db, user=user, application_id=application_id)
    if not _candidate_owns_application(db, user, application):
        raise ApplicationAccessDeniedError()
    if share_with_employer:
        application.rejection_reasons = {"reasons": reasons or [], "other_text": other_text}
    application = transition_application(
        db, application=application, to_status=ApplicationStatus.REJECTED, actor="candidate"
    )
    application = _load_application(db, application.id) or application
    notify_application_rejected(db, application)
    db.commit()
    return application


def extend_application(
    db: Session, *, user: User, company_id: uuid.UUID, application_id: uuid.UUID
) -> Application:
    require_membership(db, user=user, company_id=company_id)
    application = _load_application(db, application_id)
    if not application or application.company_id != company_id:
        raise ApplicationNotFoundError()
    if application.extended_once:
        raise ApplicationValidationError("Application already extended")
    if application.status not in (
        ApplicationStatus.SENT,
        ApplicationStatus.VIEWED,
        ApplicationStatus.REACTIVATED,
    ):
        raise InvalidTransitionError("Cannot extend in current status")
    application.expires_at = application.expires_at + timedelta(days=DEFAULT_EXPIRY_DAYS)
    application.extended_once = True
    db.commit()
    return _load_application(db, application.id) or application


def request_reactivation(db: Session, *, user: User, application_id: uuid.UUID) -> Application:
    application = get_application_for_user(db, user=user, application_id=application_id)
    if not _candidate_owns_application(db, user, application):
        raise ApplicationAccessDeniedError()
    return transition_application(
        db,
        application=application,
        to_status=ApplicationStatus.REACTIVATION_REQUESTED,
        actor="candidate",
    )


def confirm_reactivation(
    db: Session, *, user: User, company_id: uuid.UUID, application_id: uuid.UUID
) -> Application:
    require_membership(db, user=user, company_id=company_id)
    application = _load_application(db, application_id)
    if not application or application.company_id != company_id:
        raise ApplicationNotFoundError()
    return transition_application(
        db,
        application=application,
        to_status=ApplicationStatus.REACTIVATED,
        actor="employer",
    )


def close_application(db: Session, *, user: User, application_id: uuid.UUID) -> Application:
    application = get_application_for_user(db, user=user, application_id=application_id)
    if not _candidate_owns_application(db, user, application):
        raise ApplicationAccessDeniedError()
    return transition_application(
        db,
        application=application,
        to_status=ApplicationStatus.CLOSED_AFTER_ACCEPTANCE,
        actor="candidate",
    )


def expire_due_applications(db: Session, *, now: datetime | None = None) -> int:
    current = now or _now()
    statuses = (
        ApplicationStatus.SENT,
        ApplicationStatus.VIEWED,
        ApplicationStatus.REACTIVATED,
    )
    due = (
        db.query(Application)
        .filter(Application.status.in_(statuses), Application.expires_at < current)
        .all()
    )
    for application in due:
        transition_application(
            db, application=application, to_status=ApplicationStatus.EXPIRED, actor="system"
        )
    return len(due)
