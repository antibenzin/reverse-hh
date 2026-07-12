from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CompanyMemberRole, VerificationStatus
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

    members: Mapped[list[CompanyMember]] = relationship(back_populates="company")
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

