"""Company domain logic."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy.orm import Session, joinedload

from app.domain.access import (
    AccessDeniedError,
    NotMemberError,
    get_membership,
    require_membership,
    require_owner,
)
from app.domain.notifications import notify_verification_status
from app.models import (
    Company,
    CompanyInvite,
    CompanyJoinRequest,
    CompanyMember,
    User,
)
from app.models.enums import (
    CompanyMemberRole,
    InviteStatus,
    JoinRequestStatus,
    VerificationStatus,
)


class CompanyNotFoundError(Exception):
    pass


class InviteNotFoundError(Exception):
    pass


class JoinRequestNotFoundError(Exception):
    pass


class AlreadyMemberError(Exception):
    pass


class DuplicateJoinRequestError(Exception):
    pass


@dataclass(frozen=True)
class CompanyInfo:
    id: str
    name: str
    website: str | None
    tax_id: str | None
    verification_status: VerificationStatus
    is_archived: bool
    requires_manual_review: bool
    profile_data: dict | None
    my_role: CompanyMemberRole | None = None


@dataclass(frozen=True)
class MemberInfo:
    user_id: str
    email: str
    role: CompanyMemberRole


def _email_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


def _website_domain(website: str | None) -> str | None:
    if not website:
        return None
    parsed = urlparse(website if "://" in website else f"https://{website}")
    host = parsed.netloc or parsed.path
    return host.removeprefix("www.").lower() or None


def _user_company_count(db: Session, user_id: uuid.UUID) -> int:
    return db.query(CompanyMember).filter(CompanyMember.user_id == user_id).count()


def company_to_info(company: Company, *, role: CompanyMemberRole | None = None) -> CompanyInfo:
    return CompanyInfo(
        id=str(company.id),
        name=company.name,
        website=company.website,
        tax_id=company.tax_id,
        verification_status=company.verification_status,
        is_archived=company.is_archived,
        requires_manual_review=company.requires_manual_review,
        profile_data=company.profile_data,
        my_role=role,
    )


def list_user_companies(db: Session, user: User) -> list[CompanyInfo]:
    memberships = (
        db.query(CompanyMember)
        .options(joinedload(CompanyMember.company))
        .filter(CompanyMember.user_id == user.id)
        .all()
    )
    return [
        company_to_info(m.company, role=m.role)
        for m in memberships
        if not m.company.is_archived
    ]


def create_company(
    db: Session,
    *,
    user: User,
    name: str,
    website: str | None = None,
    tax_id: str | None = None,
) -> Company:
    requires_manual_review = _user_company_count(db, user.id) >= 1
    company = Company(
        name=name,
        website=website,
        tax_id=tax_id,
        requires_manual_review=requires_manual_review,
    )
    db.add(company)
    db.flush()
    db.add(
        CompanyMember(
            company_id=company.id,
            user_id=user.id,
            role=CompanyMemberRole.OWNER,
        )
    )
    db.commit()
    db.refresh(company)
    return company


def get_company_for_member(
    db: Session, *, user: User, company_id: uuid.UUID
) -> tuple[Company, CompanyMember]:
    company = db.get(Company, company_id)
    if not company:
        raise CompanyNotFoundError()
    try:
        membership = require_membership(db, user=user, company_id=company_id)
    except NotMemberError:
        raise AccessDeniedError() from None
    return company, membership


def update_company(
    db: Session,
    *,
    user: User,
    company_id: uuid.UUID,
    name: str | None = None,
    website: str | None = None,
    tax_id: str | None = None,
    profile_data: dict | None = None,
) -> Company:
    company, membership = get_company_for_member(db, user=user, company_id=company_id)
    require_owner(membership)
    if name is not None:
        company.name = name
    if website is not None:
        company.website = website
    if tax_id is not None and company.tax_id is None:
        company.tax_id = tax_id
    if profile_data is not None:
        company.profile_data = profile_data
    db.commit()
    db.refresh(company)
    return company


def archive_company(db: Session, *, user: User, company_id: uuid.UUID) -> Company:
    company, membership = get_company_for_member(db, user=user, company_id=company_id)
    require_owner(membership)
    company.is_archived = True
    db.commit()
    db.refresh(company)
    return company


def submit_verification(db: Session, *, user: User, company_id: uuid.UUID) -> Company:
    company, membership = get_company_for_member(db, user=user, company_id=company_id)
    require_owner(membership)
    if company.verification_status == VerificationStatus.VERIFIED:
        return company
    if not company.name or not company.website or not company.tax_id:
        raise ValueError("Company name, website, and tax_id are required for verification")
    email_domain = _email_domain(user.email)
    website_domain = _website_domain(company.website)
    domain_matches = website_domain is not None and email_domain == website_domain
    if company.requires_manual_review or not domain_matches:
        company.verification_status = VerificationStatus.PENDING
    else:
        company.verification_status = VerificationStatus.VERIFIED
    notify_verification_status(db, user_id=user.id, status=company.verification_status)
    db.commit()
    db.refresh(company)
    return company


def list_members(db: Session, *, user: User, company_id: uuid.UUID) -> list[MemberInfo]:
    _, membership = get_company_for_member(db, user=user, company_id=company_id)
    if membership.role not in (CompanyMemberRole.OWNER, CompanyMemberRole.RECRUITER):
        raise AccessDeniedError()
    rows = (
        db.query(CompanyMember)
        .options(joinedload(CompanyMember.user))
        .filter(CompanyMember.company_id == company_id)
        .all()
    )
    return [
        MemberInfo(user_id=str(m.user_id), email=m.user.email, role=m.role) for m in rows
    ]


def invite_recruiter(
    db: Session, *, user: User, company_id: uuid.UUID, email: str
) -> CompanyInvite:
    _, membership = get_company_for_member(db, user=user, company_id=company_id)
    require_owner(membership)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        if get_membership(db, user_id=existing_user.id, company_id=company_id):
            raise AlreadyMemberError()
    invite = CompanyInvite(
        company_id=company_id,
        email=email.lower(),
        invited_by=user.id,
        token=secrets.token_urlsafe(32),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def accept_invite(db: Session, *, user: User, token: str) -> CompanyMember:
    invite = (
        db.query(CompanyInvite)
        .filter(CompanyInvite.token == token, CompanyInvite.status == InviteStatus.PENDING)
        .first()
    )
    if not invite or invite.email != user.email.lower():
        raise InviteNotFoundError()
    if get_membership(db, user_id=user.id, company_id=invite.company_id):
        raise AlreadyMemberError()
    member = CompanyMember(
        company_id=invite.company_id,
        user_id=user.id,
        role=CompanyMemberRole.RECRUITER,
    )
    invite.status = InviteStatus.ACCEPTED
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def create_join_request(db: Session, *, user: User, company_id: uuid.UUID) -> CompanyJoinRequest:
    company = db.get(Company, company_id)
    if not company or company.is_archived:
        raise CompanyNotFoundError()
    if get_membership(db, user_id=user.id, company_id=company_id):
        raise AlreadyMemberError()
    existing = (
        db.query(CompanyJoinRequest)
        .filter(
            CompanyJoinRequest.company_id == company_id,
            CompanyJoinRequest.user_id == user.id,
            CompanyJoinRequest.status == JoinRequestStatus.PENDING,
        )
        .first()
    )
    if existing:
        raise DuplicateJoinRequestError()
    request = CompanyJoinRequest(company_id=company_id, user_id=user.id)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def approve_join_request(
    db: Session, *, user: User, company_id: uuid.UUID, request_id: uuid.UUID
) -> CompanyMember:
    _, membership = get_company_for_member(db, user=user, company_id=company_id)
    require_owner(membership)
    request = (
        db.query(CompanyJoinRequest)
        .filter(
            CompanyJoinRequest.id == request_id,
            CompanyJoinRequest.company_id == company_id,
            CompanyJoinRequest.status == JoinRequestStatus.PENDING,
        )
        .first()
    )
    if not request:
        raise JoinRequestNotFoundError()
    if get_membership(db, user_id=request.user_id, company_id=company_id):
        request.status = JoinRequestStatus.REJECTED
        db.commit()
        raise AlreadyMemberError()
    member = CompanyMember(
        company_id=company_id,
        user_id=request.user_id,
        role=CompanyMemberRole.RECRUITER,
    )
    request.status = JoinRequestStatus.APPROVED
    db.add(member)
    db.commit()
    db.refresh(member)
    return member
