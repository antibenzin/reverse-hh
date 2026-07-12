"""Resume domain logic."""

from __future__ import annotations

import copy
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.domain.resume_visibility import is_resume_in_catalog
from app.models import (
    Application,
    CandidateProfile,
    Resume,
    ResumeBlock,
    ResumeContact,
    ResumeVisibilityRule,
    ResumeWorkExperience,
    User,
)
from app.models.enums import (
    ContactType,
    ExperienceMode,
    ResumeStatus,
    ResumeVisibility,
    VisibilityRuleType,
)


class CandidateProfileRequiredError(Exception):
    pass


class ResumeNotFoundError(Exception):
    pass


class ResumeAccessDeniedError(Exception):
    pass


class ResumePublishError(Exception):
    pass


class CompanyAlreadyBlockedError(Exception):
    pass


@dataclass(frozen=True)
class ContactInput:
    type: ContactType
    value: str
    is_public: bool


@dataclass(frozen=True)
class WorkExperienceInput:
    company_name: str | None
    is_nda: bool
    role: str
    started_at: date
    ended_at: date | None
    description: str | None
    industry_id: uuid.UUID | None
    skills: list[str] | None


@dataclass(frozen=True)
class VisibilityRuleInput:
    rule_type: VisibilityRuleType
    rule_value: str


def _require_profile(db: Session, user: User) -> CandidateProfile:
    profile = (
        db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    )
    if not profile:
        raise CandidateProfileRequiredError()
    return profile


def load_resume(db: Session, resume_id: uuid.UUID) -> Resume | None:
    return (
        db.query(Resume)
        .options(
            joinedload(Resume.contacts),
            joinedload(Resume.work_experiences),
            joinedload(Resume.visibility_rules),
            joinedload(Resume.blocks),
            joinedload(Resume.test),
        )
        .filter(Resume.id == resume_id)
        .first()
    )


def get_resume_for_owner(db: Session, *, user: User, resume_id: uuid.UUID) -> Resume:
    profile = _require_profile(db, user)
    resume = load_resume(db, resume_id)
    if not resume or resume.candidate_profile_id != profile.id:
        raise ResumeNotFoundError()
    return resume


def _serialize_contacts(resume: Resume) -> list[dict[str, Any]]:
    return [
        {
            "type": contact.type.value,
            "value": contact.value,
            "is_public": contact.is_public,
        }
        for contact in resume.contacts
    ]


def _serialize_work_experiences(
    resume: Resume, *, mask_nda: bool = False
) -> list[dict[str, Any]]:
    items = []
    for exp in resume.work_experiences:
        company_name = exp.company_name
        if mask_nda and exp.is_nda:
            company_name = None
        items.append(
            {
                "company_name": company_name,
                "is_nda": exp.is_nda,
                "role": exp.role,
                "started_at": exp.started_at.isoformat(),
                "ended_at": exp.ended_at.isoformat() if exp.ended_at else None,
                "description": exp.description,
                "industry_id": str(exp.industry_id) if exp.industry_id else None,
                "skills": exp.skills or [],
            }
        )
    return items


def _serialize_visibility_rules(resume: Resume) -> list[dict[str, str]]:
    return [
        {"rule_type": rule.rule_type.value, "rule_value": rule.rule_value}
        for rule in resume.visibility_rules
    ]


def build_published_payload(resume: Resume, *, mask_nda: bool = False) -> dict[str, Any]:
    base = copy.deepcopy(resume.draft_data or {})
    if mask_nda:
        base["contacts"] = [c for c in _serialize_contacts(resume) if c["is_public"]]
    else:
        base["contacts"] = _serialize_contacts(resume)
    base["work_experiences"] = _serialize_work_experiences(resume, mask_nda=mask_nda)
    base["visibility_rules"] = _serialize_visibility_rules(resume)
    return base


def resume_to_response(resume: Resume, *, employer_view: bool = False) -> dict[str, Any]:
    if employer_view:
        payload = copy.deepcopy(resume.published_data or {})
        payload["contacts"] = [c for c in _serialize_contacts(resume) if c["is_public"]]
        payload["work_experiences"] = _serialize_work_experiences(resume, mask_nda=True)
        return {
            "id": str(resume.id),
            "title": resume.title,
            "status": resume.status.value,
            "visibility": resume.visibility.value,
            "published_data": payload,
            "draft_data": None,
            "cover_letter_required": resume.cover_letter_required,
            "has_test": resume.test is not None,
            "test_editing": resume.test_editing,
            "link_token": None,
        }

    payload = copy.deepcopy(resume.draft_data or {})
    payload["contacts"] = _serialize_contacts(resume)
    payload["work_experiences"] = _serialize_work_experiences(resume, mask_nda=False)
    payload["visibility_rules"] = _serialize_visibility_rules(resume)
    return {
        "id": str(resume.id),
        "title": resume.title,
        "status": resume.status.value,
        "visibility": resume.visibility.value,
        "published_data": resume.published_data,
        "draft_data": payload,
        "cover_letter_required": resume.cover_letter_required,
        "has_test": resume.test is not None,
        "test_editing": resume.test_editing,
        "link_token": resume.link_token,
    }


def list_own_resumes(db: Session, user: User) -> list[Resume]:
    profile = _require_profile(db, user)
    return (
        db.query(Resume)
        .options(joinedload(Resume.test))
        .filter(
            Resume.candidate_profile_id == profile.id,
            Resume.status != ResumeStatus.DELETED,
        )
        .order_by(Resume.published_at.desc().nullslast(), Resume.title)
        .all()
    )


def create_resume(db: Session, *, user: User, title: str) -> Resume:
    profile = _require_profile(db, user)
    resume = Resume(
        candidate_profile_id=profile.id,
        title=title,
        draft_data={"desired_role": title, "experience_mode": ExperienceMode.NO_EXPERIENCE.value},
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return load_resume(db, resume.id) or resume


def _replace_contacts(db: Session, resume: Resume, contacts: list[ContactInput]) -> None:
    db.query(ResumeContact).filter(ResumeContact.resume_id == resume.id).delete()
    for contact in contacts:
        db.add(
            ResumeContact(
                resume_id=resume.id,
                type=contact.type,
                value=contact.value,
                is_public=contact.is_public,
            )
        )


def _replace_work_experiences(
    db: Session, resume: Resume, experiences: list[WorkExperienceInput]
) -> None:
    db.query(ResumeWorkExperience).filter(ResumeWorkExperience.resume_id == resume.id).delete()
    for exp in experiences:
        db.add(
            ResumeWorkExperience(
                resume_id=resume.id,
                company_name=exp.company_name,
                is_nda=exp.is_nda,
                role=exp.role,
                started_at=exp.started_at,
                ended_at=exp.ended_at,
                description=exp.description,
                industry_id=exp.industry_id,
                skills=exp.skills,
            )
        )


def _replace_visibility_rules(
    db: Session, resume: Resume, rules: list[VisibilityRuleInput]
) -> None:
    db.query(ResumeVisibilityRule).filter(ResumeVisibilityRule.resume_id == resume.id).delete()
    for rule in rules:
        db.add(
            ResumeVisibilityRule(
                resume_id=resume.id,
                rule_type=rule.rule_type,
                rule_value=rule.rule_value,
            )
        )


def update_resume_draft(
    db: Session,
    *,
    user: User,
    resume_id: uuid.UUID,
    title: str | None = None,
    visibility: ResumeVisibility | None = None,
    cover_letter_required: bool | None = None,
    auto_reject_settings: dict | None = None,
    draft_data: dict | None = None,
    contacts: list[ContactInput] | None = None,
    work_experiences: list[WorkExperienceInput] | None = None,
    visibility_rules: list[VisibilityRuleInput] | None = None,
) -> Resume:
    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    if resume.status == ResumeStatus.DELETED:
        raise ResumeNotFoundError()
    if title is not None:
        resume.title = title
    if visibility is not None:
        resume.visibility = visibility
    if cover_letter_required is not None:
        resume.cover_letter_required = cover_letter_required
    if auto_reject_settings is not None:
        resume.auto_reject_settings = auto_reject_settings
    if draft_data is not None:
        merged = copy.deepcopy(resume.draft_data or {})
        merged.update(draft_data)
        resume.draft_data = merged
    if contacts is not None:
        _replace_contacts(db, resume, contacts)
    if work_experiences is not None:
        _replace_work_experiences(db, resume, work_experiences)
    if visibility_rules is not None:
        _replace_visibility_rules(db, resume, rules=visibility_rules)
    db.commit()
    return load_resume(db, resume.id) or resume


def _validate_for_publish(resume: Resume) -> None:
    data = resume.draft_data or {}
    if not resume.title:
        raise ResumePublishError("Title is required")
    if not data.get("desired_role"):
        raise ResumePublishError("Desired role is required")
    mode = data.get("experience_mode", ExperienceMode.NO_EXPERIENCE.value)
    if mode == ExperienceMode.HAS_EXPERIENCE.value and not resume.work_experiences:
        raise ResumePublishError("Work experience is required")
    if mode == ExperienceMode.NDA.value and not resume.work_experiences:
        raise ResumePublishError("Work experience is required for NDA mode")


def publish_resume(db: Session, *, user: User, resume_id: uuid.UUID) -> Resume:
    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    _validate_for_publish(resume)
    resume.published_data = build_published_payload(resume, mask_nda=False)
    resume.status = ResumeStatus.PUBLISHED
    resume.published_at = datetime.now(UTC)
    if resume.visibility == ResumeVisibility.LINK_ONLY and not resume.link_token:
        resume.link_token = secrets.token_urlsafe(16)
    if resume.visibility != ResumeVisibility.LINK_ONLY:
        resume.link_token = None
    db.commit()
    return load_resume(db, resume.id) or resume


def archive_resume(db: Session, *, user: User, resume_id: uuid.UUID) -> None:
    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    resume.status = ResumeStatus.ARCHIVED
    resume.archived_at = datetime.now(UTC)
    db.commit()


def anonymize_snapshot(snapshot: dict) -> dict:
    return {
        "anonymized": True,
        "title": "Резюме удалено",
        "desired_role": "Резюме удалено",
        "contacts": [],
        "work_experiences": [],
        "about": None,
        "portfolio_links": [],
        "certificate_links": [],
    }


def delete_resume_permanently(db: Session, *, user: User, resume_id: uuid.UUID) -> None:
    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    applications = db.query(Application).filter(Application.resume_id == resume.id).all()
    for application in applications:
        application.resume_snapshot = anonymize_snapshot(application.resume_snapshot)
    resume.status = ResumeStatus.DELETED
    resume.published_data = None
    resume.draft_data = anonymize_snapshot(resume.draft_data or {})
    resume.title = "Резюме удалено"
    db.commit()


def block_company(
    db: Session, *, user: User, resume_id: uuid.UUID, company_id: uuid.UUID
) -> None:
    from app.domain.chat import set_chats_read_only_for_company_block

    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    if any(block.company_id == company_id for block in resume.blocks):
        raise CompanyAlreadyBlockedError()
    db.add(ResumeBlock(resume_id=resume.id, company_id=company_id))
    set_chats_read_only_for_company_block(
        db, resume_id=resume.id, company_id=company_id
    )
    db.commit()


def list_catalog_resumes(db: Session, *, company) -> list[Resume]:
    resumes = (
        db.query(Resume)
        .options(
            joinedload(Resume.contacts),
            joinedload(Resume.work_experiences),
            joinedload(Resume.visibility_rules),
            joinedload(Resume.blocks),
        )
        .filter(Resume.status == ResumeStatus.PUBLISHED, Resume.test_editing.is_(False))
        .all()
    )
    return [resume for resume in resumes if is_resume_in_catalog(resume, company)]


def catalog_card(resume: Resume) -> dict[str, Any]:
    data = resume.published_data or {}
    return {
        "id": str(resume.id),
        "title": resume.title,
        "desired_role": data.get("desired_role"),
        "skills": data.get("skills", []),
        "city": data.get("city"),
        "work_formats": data.get("work_formats", []),
        "salary_min": data.get("salary_min"),
        "salary_max": data.get("salary_max"),
        "salary_currency": data.get("salary_currency"),
        "published_at": resume.published_at.isoformat() if resume.published_at else None,
    }
