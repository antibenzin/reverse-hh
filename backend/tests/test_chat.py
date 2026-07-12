import uuid

from app.models import Chat, ModerationAction
from tests.test_applications import _active_vacancy, _publish_resume, _submit
from tests.test_resumes import _auth_as


def _accepted_chat(client, cand_email: str = "chat@cand.com", emp_email: str = "chat@emp.com"):
    resume_id = _publish_resume(client, cand_email)
    company, vacancy = _active_vacancy(client, emp_email)
    _auth_as(client, emp_email)
    app_id = _submit(client, company["id"], resume_id, vacancy["id"]).json()["id"]
    _auth_as(client, cand_email)
    client.post(f"/api/v1/applications/{app_id}/view")
    accepted = client.post(f"/api/v1/applications/{app_id}/accept")
    assert accepted.status_code == 200
    return company, resume_id, app_id, accepted.json()["chat_id"]


def test_chat_not_available_before_accept(client, db_session):
    resume_id = _publish_resume(client, "nochat@cand.com")
    company, vacancy = _active_vacancy(client, "nochat@emp.com")
    _auth_as(client, "nochat@emp.com")
    _submit(client, company["id"], resume_id, vacancy["id"])

    assert db_session.query(Chat).count() == 0

    _auth_as(client, "nochat@cand.com")
    fake_chat = str(uuid.uuid4())
    assert client.get(f"/api/v1/chats/{fake_chat}/messages").status_code == 404


def test_send_and_list_messages(client):
    _auth_as(client, "send@cand.com")
    _, _, _, chat_id = _accepted_chat(client, "send@cand.com", "send@emp.com")

    sent = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"body": "Привет! Смотрите https://example.com"},
    )
    assert sent.status_code == 201
    assert sent.json()["body"].startswith("Привет")

    _auth_as(client, "send@emp.com")
    reply = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"body": "Здравствуйте"},
    )
    assert reply.status_code == 201

    messages = client.get(f"/api/v1/chats/{chat_id}/messages").json()
    assert len(messages) == 2
    assert messages[0]["body"] == "Привет! Смотрите https://example.com"


def test_send_blocked_when_closed(client):
    _, _, app_id, chat_id = _accepted_chat(client, "closed@cand.com", "closed@emp.com")
    client.post(f"/api/v1/applications/{app_id}/close")
    blocked = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"body": "ещё сообщение"},
    )
    assert blocked.status_code == 400
    assert "read-only" in blocked.json()["detail"].lower()


def test_send_blocked_when_company_blocked(client):
    company, resume_id, _, chat_id = _accepted_chat(
        client, "blockchat@cand.com", "blockchat@emp.com"
    )
    client.post(
        f"/api/v1/resumes/{resume_id}/block-company",
        json={"company_id": company["id"]},
    )
    blocked = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"body": "после блокировки"},
    )
    assert blocked.status_code == 400


def test_share_contacts_candidate_only(client):
    company, resume_id, _, chat_id = _accepted_chat(
        client, "share@cand.com", "share@emp.com"
    )
    shared = client.post(f"/api/v1/chats/{chat_id}/share-contacts")
    assert shared.status_code == 201
    assert "@public_user" in shared.json()["body"]

    _auth_as(client, "share@emp.com")
    denied = client.post(f"/api/v1/chats/{chat_id}/share-contacts")
    assert denied.status_code == 403


def test_rejects_file_attachment_payload(client):
    _, _, _, chat_id = _accepted_chat(client, "files@cand.com", "files@emp.com")
    blocked = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"body": "data:image/png;base64,abc"},
    )
    assert blocked.status_code == 400


def test_send_blocked_after_admin_sanction(client, db_session):
    company, _, _, chat_id = _accepted_chat(
        client, "admin@cand.com", "admin@emp.com"
    )
    db_session.add(
        ModerationAction(
            admin_id=uuid.uuid4(),
            action_type="block_company",
            target_type="company",
            target_id=uuid.UUID(company["id"]),
        )
    )
    db_session.commit()

    _auth_as(client, "admin@cand.com")
    blocked = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"body": "после санкции"},
    )
    assert blocked.status_code == 400
