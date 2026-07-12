import logging

from tests.test_applications import _active_vacancy, _publish_resume, _submit
from tests.test_resumes import _auth_as


def test_notification_on_application_submit(client, db_session, caplog):
    resume_id = _publish_resume(client, "notif@cand.com")
    company, vacancy = _active_vacancy(client, "notif@emp.com")
    _auth_as(client, "notif@emp.com")

    with caplog.at_level(logging.INFO):
        response = _submit(client, company["id"], resume_id, vacancy["id"])
    assert response.status_code == 201

    _auth_as(client, "notif@cand.com")
    notifications = client.get("/api/v1/notifications").json()
    assert len(notifications) == 1
    assert notifications[0]["type"] == "application_submitted"
    assert "EMAIL" in caplog.text


def test_notification_on_accept_and_email_fallback(client, caplog):
    resume_id = _publish_resume(client, "accept@cand.com")
    company, vacancy = _active_vacancy(client, "accept@emp.com")
    _auth_as(client, "accept@emp.com")
    app_id = _submit(client, company["id"], resume_id, vacancy["id"]).json()["id"]

    _auth_as(client, "accept@cand.com")
    client.post(f"/api/v1/applications/{app_id}/view")
    with caplog.at_level(logging.INFO):
        client.post(f"/api/v1/applications/{app_id}/accept")

    _auth_as(client, "accept@emp.com")
    notifications = client.get("/api/v1/notifications").json()
    types = {item["type"] for item in notifications}
    assert "application_accepted" in types
    assert "EMAIL" in caplog.text


def test_notification_on_verification(client):
    _active_vacancy(client, "verify@emp.com")
    notifications = client.get("/api/v1/notifications").json()
    assert any(item["type"] == "verification_status" for item in notifications)


def test_chat_message_creates_notification_for_recipient(client):
    from tests.test_chat import _accepted_chat

    _, _, _, chat_id = _accepted_chat(client, "msg@cand.com", "msg@emp.com")
    client.post(f"/api/v1/chats/{chat_id}/messages", json={"body": "Привет"})

    _auth_as(client, "msg@emp.com")
    notifications = client.get("/api/v1/notifications").json()
    assert any(item["type"] == "chat_message" for item in notifications)
