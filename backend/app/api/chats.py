import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.chat import (
    ChatAccessDeniedError,
    ChatNotFoundError,
    ChatReadOnlyError,
    ChatValidationError,
    list_messages,
    message_to_response,
    send_message,
    share_contacts,
)
from app.models import User

router = APIRouter(prefix="/chats", tags=["chats"])


class SendMessageBody(BaseModel):
    body: str = Field(min_length=1)


@router.get("/{chat_id}/messages")
def get_messages(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        messages = list_messages(db, user=user, chat_id=chat_id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found") from None
    except ChatAccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied") from None
    return [message_to_response(message) for message in messages]


@router.post("/{chat_id}/messages", status_code=status.HTTP_201_CREATED)
def post_message(
    chat_id: uuid.UUID,
    body: SendMessageBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        message = send_message(db, user=user, chat_id=chat_id, body=body.body)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found") from None
    except ChatAccessDeniedError:
        raise HTTPException(status_code=403, detail="Access denied") from None
    except ChatReadOnlyError:
        raise HTTPException(status_code=400, detail="Chat is read-only") from None
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return message_to_response(message)


@router.post("/{chat_id}/share-contacts", status_code=status.HTTP_201_CREATED)
def post_share_contacts(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        message = share_contacts(db, user=user, chat_id=chat_id)
    except ChatNotFoundError:
        raise HTTPException(status_code=404, detail="Chat not found") from None
    except ChatAccessDeniedError:
        raise HTTPException(status_code=403, detail="Only candidate can share contacts") from None
    except ChatReadOnlyError:
        raise HTTPException(status_code=400, detail="Chat is read-only") from None
    except ChatValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return message_to_response(message)
