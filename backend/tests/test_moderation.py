from app.models import AuditEvent, User
from tests.test_applications import _active_vacancy, _publish_resume, _submit
from tests.test_resumes import _auth_as, _register


def _make_admin(db_session, email: str) -> None:
    user = db_session.query(User).filter(User.email == email).first()
    user.is_admin = True
    db_session.commit()


def test_file_complaint_on_company(client):
    company = _active_vacancy(client, "complaint@emp.com")[0]
    _register(client, "reporter@example.com")
    created = client.post(
        "/api/v1/complaints",
        json={
            "target_type": "company",
            "target_id": company["id"],
            "body": "Нарушение правил",
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "open"


def test_non_admin_cannot_list_complaints_or_sanction(client, db_session):
    company = _active_vacancy(client, "noadmin@emp.com")[0]
    _register(client, "user@example.com")
    client.post(
        "/api/v1/complaints",
        json={
            "target_type": "company",
            "target_id": company["id"],
            "body": "Жалоба",
        },
    )
    assert client.get("/api/v1/admin/complaints").status_code == 403
    assert (
        client.post(
            "/api/v1/admin/sanctions",
            json={
                "action_type": "warning",
                "target_type": "company",
                "target_id": company["id"],
            },
        ).status_code
        == 403
    )


def test_admin_sanction_creates_audit_and_warning_for_candidate(client, db_session):
    resume_id = _publish_resume(client, "warn@cand.com")
    company, vacancy = _active_vacancy(client, "warn@emp.com")
    _auth_as(client, "warn@emp.com")
    app_id = _submit(client, company["id"], resume_id, vacancy["id"]).json()["id"]

    complaint = client.post(
        "/api/v1/complaints",
        json={
            "target_type": "company",
            "target_id": company["id"],
            "body": "Серьёзное нарушение",
        },
    ).json()

    _register(client, "admin@platform.com")
    _make_admin(db_session, "admin@platform.com")
    _auth_as(client, "admin@platform.com")

    sanctions = client.post(
        "/api/v1/admin/sanctions",
        json={
            "action_type": "serious_violation",
            "target_type": "company",
            "target_id": company["id"],
            "complaint_id": complaint["id"],
        },
    )
    assert sanctions.status_code == 201

    assert (
        db_session.query(AuditEvent)
        .filter(AuditEvent.event_type == "sanction_applied")
        .count()
        == 1
    )

    open_complaints = client.get("/api/v1/admin/complaints").json()
    assert open_complaints == []

    _auth_as(client, "warn@cand.com")
    detail = client.get(f"/api/v1/applications/{app_id}").json()
    assert detail["company_moderation_warning"] is True


def test_hide_message_sanction(client, db_session):
    from tests.test_chat import _accepted_chat

    _, _, _, chat_id = _accepted_chat(client, "hide@cand.com", "hide@emp.com")
    sent = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"body": "оскорбление"},
    ).json()
    message_id = sent["id"]

    complaint = client.post(
        "/api/v1/complaints",
        json={
            "target_type": "message",
            "target_id": message_id,
            "body": "Оскорбительное сообщение",
        },
    ).json()

    _register(client, "mod@platform.com")
    _make_admin(db_session, "mod@platform.com")
    _auth_as(client, "mod@platform.com")
    client.post(
        "/api/v1/admin/sanctions",
        json={
            "action_type": "hide_message",
            "target_type": "message",
            "target_id": message_id,
            "complaint_id": complaint["id"],
        },
    )

    _auth_as(client, "hide@cand.com")
    messages = client.get(f"/api/v1/chats/{chat_id}/messages").json()
    assert messages == []
