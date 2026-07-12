"""Chat messages on accepted applications (Epic 8)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.domain.applications import (
    ApplicationAccessDeniedError,
    ApplicationNotFoundError,
    _candidate_owns_application,
    get_application_for_user,
)
from app.models import Application, Chat, ChatMessage, ModerationAction, ResumeBlock, User
from app.models.enums import ApplicationStatus

MAX_MESSAGE_LENGTH = 5000
_DATA_URL_PATTERN = re.compile(r"data:\w+/[\w+.]+;base64", re.IGNORECASE)


class ChatNotFoundError(Exception):
    pass


class ChatAccessDeniedError(Exception):
    pass


class ChatReadOnlyError(Exception):
    pass


class ChatValidationError(Exception):
    pass


def _load_chat(db: Session, chat_id: uuid.UUID) -> Chat | None:
    return (
        db.query(Chat)
        .options(
            joinedload(Chat.application).joinedload(Application.resume),
            joinedload(Chat.messages),
        )
        .filter(Chat.id == chat_id)
        .first()
    )


def get_chat_for_user(db: Session, *, user: User, chat_id: uuid.UUID) -> Chat:
    chat = _load_chat(db, chat_id)
    if not chat:
        raise ChatNotFoundError()
    try:
        get_application_for_user(db, user=user, application_id=chat.application_id)
    except ApplicationNotFoundError:
        raise ChatNotFoundError() from None
    except ApplicationAccessDeniedError:
        raise ChatAccessDeniedError() from None
    return chat


def is_chat_read_only(db: Session, chat: Chat) -> bool:
    if chat.is_read_only:
        return True
    application = chat.application
    if application.status != ApplicationStatus.ACCEPTED:
        return True
    blocked = (
        db.query(ResumeBlock.id)
        .filter(
            ResumeBlock.resume_id == application.resume_id,
            ResumeBlock.company_id == application.company_id,
        )
        .first()
    )
    if blocked:
        return True
    sanctioned = (
        db.query(ModerationAction.id)
        .filter(
            ModerationAction.target_type == "company",
            ModerationAction.target_id == application.company_id,
            ModerationAction.action_type == "block_company",
        )
        .first()
    )
    return sanctioned is not None


def validate_message_body(body: str) -> str:
    text = body.strip()
    if not text:
        raise ChatValidationError("Message body is required")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ChatValidationError("Message too long")
    if _DATA_URL_PATTERN.search(text):
        raise ChatValidationError("File attachments are not allowed")
    return text


def message_to_response(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "sender_id": str(message.sender_id),
        "body": message.body,
        "created_at": message.created_at.isoformat(),
    }


def list_messages(db: Session, *, user: User, chat_id: uuid.UUID) -> list[ChatMessage]:
    chat = get_chat_for_user(db, user=user, chat_id=chat_id)
    return [message for message in chat.messages if not message.is_hidden]


def send_message(
    db: Session, *, user: User, chat_id: uuid.UUID, body: str
) -> ChatMessage:
    chat = get_chat_for_user(db, user=user, chat_id=chat_id)
    if is_chat_read_only(db, chat):
        raise ChatReadOnlyError()
    validated = validate_message_body(body)
    message = ChatMessage(chat_id=chat.id, sender_id=user.id, body=validated)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def share_contacts(db: Session, *, user: User, chat_id: uuid.UUID) -> ChatMessage:
    chat = get_chat_for_user(db, user=user, chat_id=chat_id)
    if not _candidate_owns_application(db, user, chat.application):
        raise ChatAccessDeniedError()
    contacts = (chat.application.resume_snapshot or {}).get("contacts") or []
    if not contacts:
        raise ChatValidationError("No public contacts to share")
    lines = ["Мои контакты:"]
    for contact in contacts:
        lines.append(f"- {contact['type']}: {contact['value']}")
    return send_message(db, user=user, chat_id=chat_id, body="\n".join(lines))


def set_chats_read_only_for_company_block(
    db: Session, *, resume_id: uuid.UUID, company_id: uuid.UUID
) -> None:
    applications = (
        db.query(Application)
        .options(joinedload(Application.chat))
        .filter(
            Application.resume_id == resume_id,
            Application.company_id == company_id,
            Application.status == ApplicationStatus.ACCEPTED,
        )
        .all()
    )
    for application in applications:
        if application.chat:
            application.chat.is_read_only = True
