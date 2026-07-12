from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import QuestionType
from app.models.types import sa_enum

if TYPE_CHECKING:
    from app.models.resume import Resume


class ResumeTest(Base):
    __tablename__ = "tests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id"), unique=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="test")
    questions: Mapped[list[TestQuestion]] = relationship(back_populates="test")


class TestQuestion(Base):
    __tablename__ = "test_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tests.id"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[QuestionType] = mapped_column(
        sa_enum(QuestionType, "question_type"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    hint: Mapped[str | None] = mapped_column(String(1000))
    scale_min: Mapped[int | None] = mapped_column(Integer)
    scale_max: Mapped[int | None] = mapped_column(Integer)
    expected_scale_min: Mapped[int | None] = mapped_column(Integer)
    expected_scale_max: Mapped[int | None] = mapped_column(Integer)

    test: Mapped[ResumeTest] = relationship(back_populates="questions")
    options: Mapped[list[TestQuestionOption]] = relationship(back_populates="question")


class TestQuestionOption(Base):
    __tablename__ = "test_question_options"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("test_questions.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    is_expected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    question: Mapped[TestQuestion] = relationship(back_populates="options")

