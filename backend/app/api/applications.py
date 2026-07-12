import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.applications import (
    ApplicationAccessDeniedError,
    ApplicationNotFoundError,
    ApplicationValidationError,
    AutoRejectConfirmationRequiredError,
    DuplicateApplicationError,
    InvalidTransitionError,
    LimitExceededError,
    TestAnswerInput,
    _candidate_owns_application,
    accept_application,
    application_to_response,
    close_application,
    confirm_reactivation,
    extend_application,
    get_application_for_user,
    list_applications,
    mark_viewed,
    reject_application,
    request_reactivation,
    submit_application,
)
from app.domain.moderation import company_has_moderation_warning
from app.models import User

router = APIRouter(prefix="/applications", tags=["applications"])


class TestAnswerSchema(BaseModel):
    question_id: uuid.UUID
    text: str | None = None
    option_ids: list[uuid.UUID] | None = None
    scale: int | None = None


class ApplicationSubmitBody(BaseModel):
    resume_id: uuid.UUID
    vacancy_id: uuid.UUID
    cover_letter: str | None = Field(default=None, min_length=300, max_length=3000)
    test_answers: list[TestAnswerSchema] | None = None
    confirm_auto_reject_risk: bool = False


class RejectBody(BaseModel):
    reasons: list[str] | None = None
    other_text: str | None = None
    share_with_employer: bool = False


def _map_answers(items: list[TestAnswerSchema] | None) -> list[TestAnswerInput] | None:
    if items is None:
        return None
    return [
        TestAnswerInput(
            question_id=item.question_id,
            text=item.text,
            option_ids=item.option_ids,
            scale=item.scale,
        )
        for item in items
    ]


def _application_response(db: Session, user: User, application) -> dict:
    warning = None
    if _candidate_owns_application(db, user, application):
        warning = company_has_moderation_warning(db, application.company_id)
    return application_to_response(application, company_moderation_warning=warning)


@router.get("")
def list_apps(
    role: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
):
    company_id = uuid.UUID(x_company_id) if x_company_id else None
    try:
        apps = list_applications(db, user=user, role=role, company_id=company_id)
    except ApplicationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return [_application_response(db, user, app) for app in apps]


@router.post("", status_code=201)
def submit_app(
    body: ApplicationSubmitBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
):
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header required")
    try:
        company_id = uuid.UUID(x_company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Company-Id") from None
    try:
        application = submit_application(
            db,
            user=user,
            company_id=company_id,
            resume_id=body.resume_id,
            vacancy_id=body.vacancy_id,
            cover_letter=body.cover_letter,
            test_answers=_map_answers(body.test_answers),
            confirm_auto_reject_risk=body.confirm_auto_reject_risk,
        )
    except DuplicateApplicationError:
        raise HTTPException(status_code=400, detail="Application already exists") from None
    except LimitExceededError:
        raise HTTPException(status_code=400, detail="Application limit exceeded") from None
    except AutoRejectConfirmationRequiredError as exc:
        raise HTTPException(status_code=400, detail={"warnings": exc.warnings}) from None
    except ApplicationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _application_response(db, user, application)


@router.get("/{application_id}")
def get_app(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        application = get_application_for_user(db, user=user, application_id=application_id)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except ApplicationAccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied") from None
    return _application_response(db, user, application)


@router.post("/{application_id}/view")
def view_app(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        application = mark_viewed(db, user=user, application_id=application_id)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except (ApplicationAccessDeniedError, InvalidTransitionError):
        raise HTTPException(status_code=400, detail="Cannot mark as viewed") from None
    return _application_response(db, user, application)


@router.post("/{application_id}/accept")
def accept_app(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        application = accept_application(db, user=user, application_id=application_id)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except (ApplicationAccessDeniedError, InvalidTransitionError):
        raise HTTPException(status_code=400, detail="Cannot accept") from None
    body = _application_response(db, user, application)
    if application.chat:
        body["chat_id"] = str(application.chat.id)
    return body


@router.post("/{application_id}/reject")
def reject_app(
    application_id: uuid.UUID,
    body: RejectBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        application = reject_application(
            db,
            user=user,
            application_id=application_id,
            reasons=body.reasons,
            other_text=body.other_text,
            share_with_employer=body.share_with_employer,
        )
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except (ApplicationAccessDeniedError, InvalidTransitionError):
        raise HTTPException(status_code=400, detail="Cannot reject") from None
    return _application_response(db, user, application)


@router.post("/{application_id}/extend")
def extend_app(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
):
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header required")
    try:
        company_id = uuid.UUID(x_company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Company-Id") from None
    try:
        application = extend_application(
            db, user=user, company_id=company_id, application_id=application_id
        )
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except (ApplicationValidationError, InvalidTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return _application_response(db, user, application)


@router.post("/{application_id}/request-reactivation")
def reactivation_request(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        application = request_reactivation(db, user=user, application_id=application_id)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except (ApplicationAccessDeniedError, InvalidTransitionError):
        raise HTTPException(status_code=400, detail="Cannot request reactivation") from None
    return _application_response(db, user, application)


@router.post("/{application_id}/confirm-reactivation")
def reactivation_confirm(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
):
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header required")
    try:
        company_id = uuid.UUID(x_company_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Company-Id") from None
    try:
        application = confirm_reactivation(
            db, user=user, company_id=company_id, application_id=application_id
        )
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except InvalidTransitionError:
        raise HTTPException(status_code=400, detail="Cannot confirm reactivation") from None
    return _application_response(db, user, application)


@router.post("/{application_id}/close")
def close_app(
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        application = close_application(db, user=user, application_id=application_id)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found") from None
    except (ApplicationAccessDeniedError, InvalidTransitionError):
        raise HTTPException(status_code=400, detail="Cannot close") from None
    return _application_response(db, user, application)
