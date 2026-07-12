"""Resume test constructor domain logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.domain.resumes import get_resume_for_owner
from app.models import ResumeTest, TestQuestion, TestQuestionOption, User
from app.models.enums import QuestionType

MAX_QUESTIONS = 10


class TestNotFoundError(Exception):
    pass


class TestValidationError(Exception):
    pass


class TestDeleteNotConfirmedError(Exception):
    pass


@dataclass(frozen=True)
class QuestionOptionInput:
    text: str
    is_expected: bool = False


@dataclass(frozen=True)
class QuestionInput:
    type: QuestionType
    text: str
    sort_order: int
    hint: str | None = None
    options: list[QuestionOptionInput] | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    expected_scale_min: int | None = None
    expected_scale_max: int | None = None


def _load_test(db: Session, resume_id: uuid.UUID) -> ResumeTest | None:
    return (
        db.query(ResumeTest)
        .options(
            joinedload(ResumeTest.questions).joinedload(TestQuestion.options),
        )
        .filter(ResumeTest.resume_id == resume_id)
        .first()
    )


def _validate_question_count(questions: list[QuestionInput]) -> None:
    if len(questions) > MAX_QUESTIONS:
        raise TestValidationError(f"Maximum {MAX_QUESTIONS} questions allowed")
    if not questions:
        raise TestValidationError("At least one question is required to publish")


def _validate_question(question: QuestionInput, *, for_publish: bool) -> None:
    if not question.text.strip():
        raise TestValidationError("Question text is required")
    if question.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE):
        options = question.options or []
        if for_publish and len(options) < 2:
            raise TestValidationError("Choice questions require at least two options")
        expected = [o for o in options if o.is_expected]
        if for_publish and question.type == QuestionType.SINGLE_CHOICE and len(expected) != 1:
            raise TestValidationError("Single choice requires exactly one expected option")
        if for_publish and question.type == QuestionType.MULTI_CHOICE and not expected:
            raise TestValidationError("Multi choice requires at least one expected option")
    if question.type == QuestionType.SCALE:
        if question.scale_min is None or question.scale_max is None:
            raise TestValidationError("Scale questions require scale_min and scale_max")
        if question.scale_min >= question.scale_max:
            raise TestValidationError("scale_max must be greater than scale_min")


def _replace_questions(db: Session, test: ResumeTest, questions: list[QuestionInput]) -> None:
    for question in test.questions:
        db.query(TestQuestionOption).filter(
            TestQuestionOption.question_id == question.id
        ).delete()
    db.query(TestQuestion).filter(TestQuestion.test_id == test.id).delete()
    for question in questions:
        row = TestQuestion(
            test_id=test.id,
            sort_order=question.sort_order,
            type=question.type,
            text=question.text,
            hint=question.hint,
            scale_min=question.scale_min,
            scale_max=question.scale_max,
            expected_scale_min=question.expected_scale_min,
            expected_scale_max=question.expected_scale_max,
        )
        db.add(row)
        db.flush()
        if question.options:
            for option in question.options:
                db.add(
                    TestQuestionOption(
                        question_id=row.id,
                        text=option.text,
                        is_expected=option.is_expected,
                    )
                )


def test_to_response(test: ResumeTest, *, hide_scoring: bool = False) -> dict[str, Any]:
    questions = sorted(test.questions, key=lambda q: q.sort_order)
    return {
        "id": str(test.id),
        "resume_id": str(test.resume_id),
        "version": test.version,
        "is_published": test.is_published,
        "questions": [
            {
                "id": str(q.id),
                "sort_order": q.sort_order,
                "type": q.type.value,
                "text": q.text,
                "hint": q.hint,
                "scale_min": q.scale_min,
                "scale_max": q.scale_max,
                "expected_scale_min": None if hide_scoring else q.expected_scale_min,
                "expected_scale_max": None if hide_scoring else q.expected_scale_max,
                "options": [
                    {
                        "id": str(o.id),
                        "text": o.text,
                        "is_expected": None if hide_scoring else o.is_expected,
                    }
                    for o in q.options
                ],
            }
            for q in questions
        ],
    }


def get_test_for_resume(db: Session, *, user: User, resume_id: uuid.UUID) -> ResumeTest:
    get_resume_for_owner(db, user=user, resume_id=resume_id)
    test = _load_test(db, resume_id)
    if not test:
        raise TestNotFoundError()
    return test


def save_test_draft(
    db: Session,
    *,
    user: User,
    resume_id: uuid.UUID,
    questions: list[QuestionInput],
) -> ResumeTest:
    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    if len(questions) > MAX_QUESTIONS:
        raise TestValidationError(f"Maximum {MAX_QUESTIONS} questions allowed")
    for question in questions:
        _validate_question(question, for_publish=False)

    test = _load_test(db, resume_id)
    if not test:
        test = ResumeTest(resume_id=resume_id)
        db.add(test)
        db.flush()
    _replace_questions(db, test, questions)
    resume.test_editing = True
    test.is_published = False
    db.commit()
    return _load_test(db, resume_id) or test


def publish_test(db: Session, *, user: User, resume_id: uuid.UUID) -> ResumeTest:
    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    test = _load_test(db, resume_id)
    if not test:
        raise TestNotFoundError()
    questions = sorted(test.questions, key=lambda q: q.sort_order)
    if not questions:
        raise TestValidationError("At least one question is required to publish")
    if len(questions) > MAX_QUESTIONS:
        raise TestValidationError(f"Maximum {MAX_QUESTIONS} questions allowed")
    inputs = [
        QuestionInput(
            type=q.type,
            text=q.text,
            sort_order=q.sort_order,
            hint=q.hint,
            options=[
                QuestionOptionInput(text=o.text, is_expected=o.is_expected) for o in q.options
            ]
            or None,
            scale_min=q.scale_min,
            scale_max=q.scale_max,
            expected_scale_min=q.expected_scale_min,
            expected_scale_max=q.expected_scale_max,
        )
        for q in questions
    ]
    _validate_question_count(inputs)
    for question in inputs:
        _validate_question(question, for_publish=True)

    if test.is_published:
        test.version += 1
    else:
        test.is_published = True
    resume.test_editing = False
    db.commit()
    return _load_test(db, resume_id) or test


def delete_test(
    db: Session, *, user: User, resume_id: uuid.UUID, confirm: bool
) -> None:
    if not confirm:
        raise TestDeleteNotConfirmedError()
    resume = get_resume_for_owner(db, user=user, resume_id=resume_id)
    test = _load_test(db, resume_id)
    if not test:
        raise TestNotFoundError()
    for question in test.questions:
        db.query(TestQuestionOption).filter(
            TestQuestionOption.question_id == question.id
        ).delete()
    db.query(TestQuestion).filter(TestQuestion.test_id == test.id).delete()
    db.delete(test)
    resume.test_editing = False
    db.commit()
