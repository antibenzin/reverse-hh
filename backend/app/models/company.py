from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CompanyMemberRole, InviteStatus, JoinRequestStatus, VerificationStatus
from app.models.types import sa_enum

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User
    from app.models.vacancy import Vacancy


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(512))
    tax_id: Mapped[str | None] = mapped_column(String(64))
    verification_status: Mapped[VerificationStatus] = mapped_column(
        sa_enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
        nullable=False,
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    profile_data: Mapped[dict | None] = mapped_column(JSON)
    application_limit_monthly: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_used_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    members: Mapped[list[CompanyMember]] = relationship(back_populates="company")
    invites: Mapped[list[CompanyInvite]] = relationship(back_populates="company")
    join_requests: Mapped[list[CompanyJoinRequest]] = relationship(back_populates="company")
    vacancies: Mapped[list[Vacancy]] = relationship(back_populates="company")
    applications: Mapped[list[Application]] = relationship(back_populates="company")


class CompanyMember(Base):
    __tablename__ = "company_members"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_members_company_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role: Mapped[CompanyMemberRole] = mapped_column(
        sa_enum(CompanyMemberRole, "company_member_role"),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="company_memberships")
    company: Mapped[Company] = relationship(back_populates="members")


class CompanyInvite(Base):
    __tablename__ = "company_invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        sa_enum(InviteStatus, "invite_status"),
        default=InviteStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="invites")


class CompanyJoinRequest(Base):
    __tablename__ = "company_join_requests"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_join_requests_company_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[JoinRequestStatus] = mapped_column(
        sa_enum(JoinRequestStatus, "join_request_status"),
        default=JoinRequestStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped[Company] = relationship(back_populates="join_requests")
    user: Mapped[User] = relationship()

