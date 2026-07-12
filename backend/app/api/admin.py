import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.moderation import (
    AdminRequiredError,
    ComplaintNotFoundError,
    ModerationValidationError,
    apply_sanction,
    complaint_to_response,
    list_open_complaints,
    sanction_to_response,
)
from app.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


class SanctionBody(BaseModel):
    action_type: str
    target_type: str
    target_id: uuid.UUID
    complaint_id: uuid.UUID | None = None
    note: str | None = None


@router.get("/complaints")
def get_complaints(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        complaints = list_open_complaints(db, user=user)
    except AdminRequiredError:
        raise HTTPException(status_code=403, detail="Admin required") from None
    return [complaint_to_response(complaint) for complaint in complaints]


@router.post("/sanctions", status_code=status.HTTP_201_CREATED)
def post_sanction(
    body: SanctionBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        action = apply_sanction(
            db,
            admin=user,
            action_type=body.action_type,
            target_type=body.target_type,
            target_id=body.target_id,
            complaint_id=body.complaint_id,
            note=body.note,
        )
    except AdminRequiredError:
        raise HTTPException(status_code=403, detail="Admin required") from None
    except ComplaintNotFoundError:
        raise HTTPException(status_code=404, detail="Complaint not found") from None
    except ModerationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return sanction_to_response(action)
