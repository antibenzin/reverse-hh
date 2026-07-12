"""In-app notifications and email hooks for key domain events."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import Application, Chat, Notification, User
from app.models.enums import ApplicationStatus, VerificationStatus
from app.services.email import send_email


def notification_to_response(notification: Notification) -> dict[str, Any]:
    return {
        "id": str(notification.id),
        "type": notification.type,
        "body": notification.body,
        "link": notification.link,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
    }


def list_notifications(db: Session, *, user: User) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


def _notify(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: str,
    body: str,
    link: str | None = None,
    email: str | None = None,
    email_subject: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        body=body,
        link=link,
    )
    db.add(notification)
    if email:
        send_email(to=email, subject=email_subject or "Reverse HH", body=body)
    return notification


def _user_email(db: Session, user_id: uuid.UUID) -> str | None:
    user = db.get(User, user_id)
    return user.email if user else None


def notify_application_submitted(db: Session, application: Application) -> None:
    if application.status != ApplicationStatus.SENT:
        return
    profile = application.resume.candidate_profile
    if not profile:
        return
    body = "Новый отклик на ваше резюме"
    link = f"/pages/candidate/applications.html?id={application.id}"
    _notify(
        db,
        user_id=profile.user_id,
        notification_type="application_submitted",
        body=body,
        link=link,
        email=_user_email(db, profile.user_id),
        email_subject="Новый отклик",
    )


def notify_application_accepted(db: Session, application: Application) -> None:
    body = "Кандидат принял ваш отклик"
    link = f"/pages/employer/applications.html?id={application.id}"
    _notify(
        db,
        user_id=application.sent_by,
        notification_type="application_accepted",
        body=body,
        link=link,
        email=_user_email(db, application.sent_by),
        email_subject="Отклик принят",
    )


def notify_application_rejected(db: Session, application: Application) -> None:
    body = "Кандидат отклонил ваш отклик"
    link = f"/pages/employer/applications.html?id={application.id}"
    _notify(
        db,
        user_id=application.sent_by,
        notification_type="application_rejected",
        body=body,
        link=link,
        email=_user_email(db, application.sent_by),
        email_subject="Отклик отклонён",
    )


def notify_chat_message(
    db: Session, *, chat: Chat, sender: User, recipient_id: uuid.UUID
) -> None:
    if sender.id == recipient_id:
        return
    body = "Новое сообщение в чате"
    link = f"/pages/chat.html?application_id={chat.application_id}"
    _notify(
        db,
        user_id=recipient_id,
        notification_type="chat_message",
        body=body,
        link=link,
        email=_user_email(db, recipient_id),
        email_subject="Новое сообщение",
    )


def notify_verification_status(
    db: Session, *, user_id: uuid.UUID, status: VerificationStatus
) -> None:
    if status == VerificationStatus.VERIFIED:
        body = "Компания верифицирована"
        subject = "Верификация пройдена"
    elif status == VerificationStatus.PENDING:
        body = "Заявка на верификацию отправлена на проверку"
        subject = "Верификация на проверке"
    else:
        return
    _notify(
        db,
        user_id=user_id,
        notification_type="verification_status",
        body=body,
        link="/pages/employer/company.html",
        email=_user_email(db, user_id),
        email_subject=subject,
    )
