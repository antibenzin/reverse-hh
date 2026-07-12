"""Vacancy domain logic (ADR-0004)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.domain.access import AccessDeniedError, NotMemberError, require_membership
from app.models import CompanyMember, User, Vacancy, VacancyRecruiter
from app.models.enums import CompanyMemberRole, VacancyStatus

REQUIRED_DATA_FIELDS = (
    "title",
    "currency",
    "work_format",
    "city",
    "country",
    "employment_type",
    "responsibilities",
    "requirements",
    "hiring_stages",
    "sender_name",
    "sender_role",
)


class VacancyNotFoundError(Exception):
    pass


class VacancyValidationError(Exception):
    pass


@dataclass(frozen=True)
class VacancyInfo:
    id: str
    company_id: str
    status: VacancyStatus
    created_by: str
    data: dict[str, Any]
    recruiter_ids: list[str]


def _has_required_salary(data: dict[str, Any]) -> bool:
    if data.get("salary_fixed") is not None:
        return True
    return data.get("salary_min") is not None and data.get("salary_max") is not None


def validate_vacancy_data(data: dict[str, Any], *, for_active: bool) -> None:
    if not for_active:
        return
    missing = [field for field in REQUIRED_DATA_FIELDS if not data.get(field)]
    if missing:
        raise VacancyValidationError(f"Missing required fields: {', '.join(missing)}")
    if not _has_required_salary(data):
        raise VacancyValidationError("Salary fixed or salary range is required")


def _load_vacancy(db: Session, company_id: uuid.UUID, vacancy_id: uuid.UUID) -> Vacancy | None:
    return (
        db.query(Vacancy)
        .options(joinedload(Vacancy.recruiters))
        .filter(Vacancy.id == vacancy_id, Vacancy.company_id == company_id)
        .first()
    )


def _is_assigned_recruiter(vacancy: Vacancy, user_id: uuid.UUID) -> bool:
    return any(r.user_id == user_id for r in vacancy.recruiters)


def can_view_vacancy(membership: CompanyMember, vacancy: Vacancy, user_id: uuid.UUID) -> bool:
    if membership.role == CompanyMemberRole.OWNER:
        return True
    return vacancy.created_by == user_id or _is_assigned_recruiter(vacancy, user_id)


def can_edit_vacancy(membership: CompanyMember, vacancy: Vacancy, user_id: uuid.UUID) -> bool:
    if membership.role == CompanyMemberRole.OWNER:
        return True
    return vacancy.created_by == user_id or _is_assigned_recruiter(vacancy, user_id)


def can_change_status(membership: CompanyMember, vacancy: Vacancy, user_id: uuid.UUID) -> bool:
    if membership.role == CompanyMemberRole.OWNER:
        return True
    return vacancy.created_by == user_id


def vacancy_to_info(vacancy: Vacancy) -> VacancyInfo:
    return VacancyInfo(
        id=str(vacancy.id),
        company_id=str(vacancy.company_id),
        status=vacancy.status,
        created_by=str(vacancy.created_by),
        data=vacancy.data or {},
        recruiter_ids=[str(r.user_id) for r in vacancy.recruiters],
    )


def list_vacancies(db: Session, *, user: User, company_id: uuid.UUID) -> list[VacancyInfo]:
    try:
        membership = require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise AccessDeniedError() from None
    query = (
        db.query(Vacancy)
        .options(joinedload(Vacancy.recruiters))
        .filter(Vacancy.company_id == company_id)
    )
    vacancies = query.all()
    if membership.role == CompanyMemberRole.OWNER:
        visible = vacancies
    else:
        visible = [
            v
            for v in vacancies
            if can_view_vacancy(membership, v, user.id)
        ]
    return [vacancy_to_info(v) for v in visible]


def create_vacancy(
    db: Session, *, user: User, company_id: uuid.UUID, data: dict[str, Any]
) -> Vacancy:
    try:
        require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise AccessDeniedError() from None
    vacancy = Vacancy(
        company_id=company_id,
        created_by=user.id,
        data=data,
        status=VacancyStatus.DRAFT,
    )
    db.add(vacancy)
    db.flush()
    db.add(VacancyRecruiter(vacancy_id=vacancy.id, user_id=user.id))
    db.commit()
    return _load_vacancy(db, company_id, vacancy.id) or vacancy


def update_vacancy(
    db: Session,
    *,
    user: User,
    company_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    data: dict[str, Any],
) -> Vacancy:
    try:
        membership = require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise AccessDeniedError() from None
    vacancy = _load_vacancy(db, company_id, vacancy_id)
    if not vacancy:
        raise VacancyNotFoundError()
    if not can_edit_vacancy(membership, vacancy, user.id):
        raise AccessDeniedError()
    merged = dict(vacancy.data or {})
    merged.update(data)
    vacancy.data = merged
    db.commit()
    return _load_vacancy(db, company_id, vacancy_id) or vacancy


def set_vacancy_status(
    db: Session,
    *,
    user: User,
    company_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    status: VacancyStatus,
) -> Vacancy:
    try:
        membership = require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise AccessDeniedError() from None
    vacancy = _load_vacancy(db, company_id, vacancy_id)
    if not vacancy:
        raise VacancyNotFoundError()
    if not can_change_status(membership, vacancy, user.id):
        raise AccessDeniedError()
    if status == VacancyStatus.ACTIVE:
        validate_vacancy_data(vacancy.data or {}, for_active=True)
    vacancy.status = status
    db.commit()
    return _load_vacancy(db, company_id, vacancy_id) or vacancy


def assign_recruiters(
    db: Session,
    *,
    user: User,
    company_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    recruiter_ids: list[uuid.UUID],
) -> Vacancy:
    try:
        membership = require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise AccessDeniedError() from None
    vacancy = _load_vacancy(db, company_id, vacancy_id)
    if not vacancy:
        raise VacancyNotFoundError()
    if not can_change_status(membership, vacancy, user.id):
        raise AccessDeniedError()
    db.query(VacancyRecruiter).filter(VacancyRecruiter.vacancy_id == vacancy.id).delete()
    assignees = set(recruiter_ids)
    assignees.add(vacancy.created_by)
    for recruiter_id in assignees:
        db.add(VacancyRecruiter(vacancy_id=vacancy.id, user_id=recruiter_id))
    db.commit()
    return _load_vacancy(db, company_id, vacancy_id) or vacancy
