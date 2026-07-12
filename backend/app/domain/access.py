"""Company workspace access checks (ADR-0004)."""

from __future__ import annotations

import uuid

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.models import Company, CompanyMember, User
from app.models.enums import CompanyMemberRole


class AccessDeniedError(Exception):
    pass


class NotMemberError(Exception):
    pass


def get_membership(
    db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID
) -> CompanyMember | None:
    return (
        db.query(CompanyMember)
        .filter(CompanyMember.user_id == user_id, CompanyMember.company_id == company_id)
        .first()
    )


def require_membership(
    db: Session, *, user: User, company_id: uuid.UUID
) -> CompanyMember:
    membership = get_membership(db, user_id=user.id, company_id=company_id)
    if not membership:
        raise NotMemberError()
    return membership


def require_owner(membership: CompanyMember) -> None:
    if membership.role != CompanyMemberRole.OWNER:
        raise AccessDeniedError()


def resolve_workspace_company(
    db: Session,
    *,
    user: User,
    company_id: uuid.UUID | None,
) -> tuple[Company, CompanyMember]:
    if not company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header required")
    company = db.get(Company, company_id)
    if not company or company.is_archived:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        membership = require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
    return company, membership


def get_workspace_membership(
    db: Session,
    user: User,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
) -> CompanyMember:
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header required")
    try:
        company_id = uuid.UUID(x_company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Company-Id") from None
    try:
        return require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise HTTPException(status_code=403, detail="Not a company member") from None
