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
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ApplicationStatus
from app.models.types import UuidArray, sa_enum

if TYPE_CHECKING:
    from app.models.chat import Chat
    from app.models.company import Company
    from app.models.resume import Resume
    from app.models.vacancy import Vacancy


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("resume_id", "vacancy_id", name="uq_applications_resume_vacancy"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id"), nullable=False
    )
    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("vacancies.id"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    sent_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        sa_enum(ApplicationStatus, "application_status"),
        nullable=False,
    )
    resume_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    vacancy_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    test_snapshot: Mapped[dict | None] = mapped_column(JSON)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    rejection_reasons: Mapped[dict | None] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    employer_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extended_once: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    limit_debited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    resume: Mapped[Resume] = relationship(back_populates="applications")
    vacancy: Mapped[Vacancy] = relationship(back_populates="applications")
    company: Mapped[Company] = relationship(back_populates="applications")
    test_answers: Mapped[list[ApplicationTestAnswer]] = relationship(
        back_populates="application"
    )
    chat: Mapped[Chat | None] = relationship(back_populates="application", uselist=False)


class ApplicationTestAnswer(Base):
    __tablename__ = "application_test_answers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("applications.id"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text)
    answer_options: Mapped[list[uuid.UUID] | None] = mapped_column(UuidArray())
    answer_scale: Mapped[int | None] = mapped_column(Integer)

    application: Mapped[Application] = relationship(back_populates="test_answers")

