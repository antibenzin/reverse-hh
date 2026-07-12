from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    ContactType,
    ResumeStatus,
    ResumeVisibility,
    VisibilityRuleType,
)
from app.models.types import sa_enum

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.assessment import ResumeTest
    from app.models.user import CandidateProfile


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("candidate_profiles.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ResumeStatus] = mapped_column(
        sa_enum(ResumeStatus, "resume_status"),
        default=ResumeStatus.DRAFT,
        nullable=False,
    )
    visibility: Mapped[ResumeVisibility] = mapped_column(
        sa_enum(ResumeVisibility, "resume_visibility"),
        default=ResumeVisibility.PUBLIC,
        nullable=False,
    )
    link_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    published_data: Mapped[dict | None] = mapped_column(JSON)
    draft_data: Mapped[dict | None] = mapped_column(JSON)
    cover_letter_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_reject_settings: Mapped[dict | None] = mapped_column(JSON)
    test_editing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    candidate_profile: Mapped[CandidateProfile] = relationship(back_populates="resumes")
    work_experiences: Mapped[list[ResumeWorkExperience]] = relationship(back_populates="resume")
    contacts: Mapped[list[ResumeContact]] = relationship(back_populates="resume")
    visibility_rules: Mapped[list[ResumeVisibilityRule]] = relationship(back_populates="resume")
    blocks: Mapped[list[ResumeBlock]] = relationship(back_populates="resume")
    test: Mapped[ResumeTest | None] = relationship(back_populates="resume", uselist=False)
    applications: Mapped[list[Application]] = relationship(back_populates="resume")


class ResumeWorkExperience(Base):
    __tablename__ = "resume_work_experiences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id"), nullable=False
    )
    company_name: Mapped[str | None] = mapped_column(String(255))
    is_nda: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[date] = mapped_column(Date, nullable=False)
    ended_at: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    industry_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    skills: Mapped[list | None] = mapped_column(JSON)

    resume: Mapped[Resume] = relationship(back_populates="work_experiences")


class ResumeContact(Base):
    __tablename__ = "resume_contacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id"), nullable=False
    )
    type: Mapped[ContactType] = mapped_column(
        sa_enum(ContactType, "contact_type"),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="contacts")


class ResumeVisibilityRule(Base):
    __tablename__ = "resume_visibility_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id"), nullable=False
    )
    rule_type: Mapped[VisibilityRuleType] = mapped_column(
        sa_enum(VisibilityRuleType, "visibility_rule_type"),
        nullable=False,
    )
    rule_value: Mapped[str] = mapped_column(String(255), nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="visibility_rules")


class ResumeBlock(Base):
    __tablename__ = "resume_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )

    resume: Mapped[Resume] = relationship(back_populates="blocks")

