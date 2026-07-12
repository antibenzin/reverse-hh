import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.resumes import ResumeNotFoundError
from app.domain.tests import (
    QuestionInput,
    QuestionOptionInput,
    TestDeleteNotConfirmedError,
    TestNotFoundError,
    TestValidationError,
    delete_test,
    get_test_for_resume,
    publish_test,
    save_test_draft,
    test_to_response,
)
from app.models import User
from app.models.enums import QuestionType

router = APIRouter(prefix="/resumes", tags=["tests"])


class QuestionOptionSchema(BaseModel):
    text: str = Field(min_length=1, max_length=255)
    is_expected: bool = False


class QuestionSchema(BaseModel):
    type: QuestionType
    text: str = Field(min_length=1, max_length=500)
    sort_order: int = Field(ge=0)
    hint: str | None = Field(default=None, max_length=1000)
    options: list[QuestionOptionSchema] | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    expected_scale_min: int | None = None
    expected_scale_max: int | None = None


class TestSaveRequest(BaseModel):
    questions: list[QuestionSchema]


def _map_questions(items: list[QuestionSchema]) -> list[QuestionInput]:
    return [
        QuestionInput(
            type=item.type,
            text=item.text,
            sort_order=item.sort_order,
            hint=item.hint,
            options=[
                QuestionOptionInput(text=o.text, is_expected=o.is_expected)
                for o in (item.options or [])
            ]
            or None,
            scale_min=item.scale_min,
            scale_max=item.scale_max,
            expected_scale_min=item.expected_scale_min,
            expected_scale_max=item.expected_scale_max,
        )
        for item in items
    ]


def _handle_errors(exc: Exception) -> None:
    if isinstance(exc, ResumeNotFoundError):
        raise HTTPException(status_code=404, detail="Resume not found") from None
    if isinstance(exc, TestNotFoundError):
        raise HTTPException(status_code=404, detail="Test not found") from None
    raise exc


@router.get("/{resume_id}/test")
def get_test(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        test = get_test_for_resume(db, user=user, resume_id=resume_id)
    except Exception as exc:
        _handle_errors(exc)
    return test_to_response(test)


@router.put("/{resume_id}/test")
def save_test(
    resume_id: uuid.UUID,
    body: TestSaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        test = save_test_draft(
            db, user=user, resume_id=resume_id, questions=_map_questions(body.questions)
        )
    except TestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception as exc:
        _handle_errors(exc)
    return test_to_response(test)


@router.post("/{resume_id}/test/publish")
def publish_test_endpoint(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        test = publish_test(db, user=user, resume_id=resume_id)
    except TestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except Exception as exc:
        _handle_errors(exc)
    return test_to_response(test)


@router.delete("/{resume_id}/test", status_code=204)
def delete_test_endpoint(
    resume_id: uuid.UUID,
    confirm: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        delete_test(db, user=user, resume_id=resume_id, confirm=confirm)
    except TestDeleteNotConfirmedError:
        raise HTTPException(status_code=400, detail="Confirmation required") from None
    except Exception as exc:
        _handle_errors(exc)
    return None
