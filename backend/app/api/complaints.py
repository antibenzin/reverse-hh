import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.moderation import (
    ModerationValidationError,
    complaint_to_response,
    file_complaint,
)
from app.models import User
from app.models.enums import ComplaintTargetType

router = APIRouter(tags=["complaints"])


class ComplaintBody(BaseModel):
    target_type: ComplaintTargetType
    target_id: uuid.UUID
    body: str = Field(min_length=1)


@router.post("/complaints", status_code=status.HTTP_201_CREATED)
def post_complaint(
    body: ComplaintBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        complaint = file_complaint(
            db,
            user=user,
            target_type=body.target_type,
            target_id=body.target_id,
            body=body.body,
        )
    except ModerationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return complaint_to_response(complaint)
