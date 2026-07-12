"""Complaints, sanctions, and moderation side effects."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.domain.applications import ApplicationNotFoundError, get_application_for_user
from app.domain.audit import record_audit_event
from app.models import (
    Application,
    ChatMessage,
    Company,
    Complaint,
    ModerationAction,
    Resume,
    User,
)
from app.models.enums import (
    ApplicationStatus,
    ComplaintStatus,
    ComplaintTargetType,
    VerificationStatus,
)

SANCTION_TYPES = frozenset(
    {
        "warning",
        "serious_violation",
        "block_company",
        "block_user",
        "hide_message",
        "revoke_verification",
    }
)
WARNING_ACTION_TYPES = frozenset({"warning", "serious_violation", "block_company"})


class ModerationValidationError(Exception):
    pass


class ComplaintNotFoundError(Exception):
    pass


class AdminRequiredError(Exception):
    pass


def require_admin(user: User) -> None:
    if not user.is_admin:
        raise AdminRequiredError()


def company_has_moderation_warning(db: Session, company_id: uuid.UUID) -> bool:
    return (
        db.query(ModerationAction.id)
        .filter(
            ModerationAction.target_type == "company",
            ModerationAction.target_id == company_id,
            ModerationAction.action_type.in_(WARNING_ACTION_TYPES),
        )
        .first()
        is not None
    )


def _validate_complaint_target(
    db: Session, *, user: User, target_type: ComplaintTargetType, target_id: uuid.UUID
) -> None:
    if target_type == ComplaintTargetType.COMPANY:
        if not db.get(Company, target_id):
            raise ModerationValidationError("Company not found")
        return
    if target_type == ComplaintTargetType.RESUME:
        if not db.get(Resume, target_id):
            raise ModerationValidationError("Resume not found")
        return
    if target_type == ComplaintTargetType.APPLICATION:
        try:
            get_application_for_user(db, user=user, application_id=target_id)
        except ApplicationNotFoundError:
            raise ModerationValidationError("Application not found") from None
        return
    if target_type == ComplaintTargetType.MESSAGE:
        message = db.get(ChatMessage, target_id)
        if not message:
            raise ModerationValidationError("Message not found")
        return
    raise ModerationValidationError("Invalid target type")


def file_complaint(
    db: Session,
    *,
    user: User,
    target_type: ComplaintTargetType,
    target_id: uuid.UUID,
    body: str,
) -> Complaint:
    text = body.strip()
    if not text:
        raise ModerationValidationError("Complaint body is required")
    _validate_complaint_target(db, user=user, target_type=target_type, target_id=target_id)
    complaint = Complaint(
        reporter_id=user.id,
        target_type=target_type,
        target_id=target_id,
        body=text,
        status=ComplaintStatus.OPEN,
    )
    db.add(complaint)
    db.flush()
    record_audit_event(
        db,
        actor_id=user.id,
        event_type="complaint_filed",
        entity_type="complaint",
        entity_id=complaint.id,
        payload={"target_type": target_type.value, "target_id": str(target_id)},
    )
    db.commit()
    db.refresh(complaint)
    return complaint


def complaint_to_response(complaint: Complaint) -> dict[str, Any]:
    return {
        "id": str(complaint.id),
        "reporter_id": str(complaint.reporter_id),
        "target_type": complaint.target_type.value,
        "target_id": str(complaint.target_id),
        "body": complaint.body,
        "status": complaint.status.value,
        "created_at": complaint.created_at.isoformat(),
    }


def list_open_complaints(db: Session, *, user: User) -> list[Complaint]:
    require_admin(user)
    return (
        db.query(Complaint)
        .filter(Complaint.status == ComplaintStatus.OPEN)
        .order_by(Complaint.created_at.desc())
        .all()
    )


def _set_company_chats_read_only(db: Session, company_id: uuid.UUID) -> None:
    applications = (
        db.query(Application)
        .options(joinedload(Application.chat))
        .filter(
            Application.company_id == company_id,
            Application.status == ApplicationStatus.ACCEPTED,
        )
        .all()
    )
    for application in applications:
        if application.chat:
            application.chat.is_read_only = True


def _apply_sanction_side_effects(
    db: Session,
    *,
    action_type: str,
    target_type: str,
    target_id: uuid.UUID,
) -> None:
    if action_type == "hide_message" and target_type == "message":
        message = db.get(ChatMessage, target_id)
        if message:
            message.is_hidden = True
        return
    if action_type == "revoke_verification" and target_type == "company":
        company = db.get(Company, target_id)
        if company:
            company.verification_status = VerificationStatus.SUSPENDED
        return
    if action_type == "block_company" and target_type == "company":
        _set_company_chats_read_only(db, target_id)
        return


def apply_sanction(
    db: Session,
    *,
    admin: User,
    action_type: str,
    target_type: str,
    target_id: uuid.UUID,
    complaint_id: uuid.UUID | None = None,
    note: str | None = None,
) -> ModerationAction:
    require_admin(admin)
    if action_type not in SANCTION_TYPES:
        raise ModerationValidationError("Invalid sanction type")
    complaint: Complaint | None = None
    if complaint_id:
        complaint = db.get(Complaint, complaint_id)
        if not complaint:
            raise ComplaintNotFoundError()
    action = ModerationAction(
        complaint_id=complaint_id,
        admin_id=admin.id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        note=note,
    )
    db.add(action)
    _apply_sanction_side_effects(
        db, action_type=action_type, target_type=target_type, target_id=target_id
    )
    if complaint:
        complaint.status = ComplaintStatus.RESOLVED
    record_audit_event(
        db,
        actor_id=admin.id,
        event_type="sanction_applied",
        entity_type=target_type,
        entity_id=target_id,
        payload={
            "action_type": action_type,
            "complaint_id": str(complaint_id) if complaint_id else None,
            "note": note,
        },
    )
    db.commit()
    db.refresh(action)
    return action


def sanction_to_response(action: ModerationAction) -> dict[str, Any]:
    return {
        "id": str(action.id),
        "complaint_id": str(action.complaint_id) if action.complaint_id else None,
        "admin_id": str(action.admin_id),
        "action_type": action.action_type,
        "target_type": action.target_type,
        "target_id": str(action.target_id),
        "note": action.note,
        "created_at": action.created_at.isoformat(),
    }
