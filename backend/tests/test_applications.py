import uuid
from datetime import UTC, datetime, timedelta

from app.domain.applications import expire_due_applications
from app.models import Application, Company, Resume
from tests.test_resumes import (
    _auth_as,
    _create_profile,
    _create_verified_company,
    _register,
    _resume_payload,
)
from tests.test_vacancies import FULL_VACANCY_DATA

COVER_LETTER = "x" * 300


def _publish_resume(client, email: str = "cand@app.com"):
    _register(client, email)
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "Dev"}).json()["id"]
    client.patch(f"/api/v1/resumes/{resume_id}", json=_resume_payload())
    client.post(f"/api/v1/resumes/{resume_id}/publish")
    return resume_id


def _active_vacancy(client, email: str = "emp@app.com", company_name: str = "App Co"):
    company = _create_verified_company(client, email, name=company_name)
    vacancy = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": {"title": "Role"}},
    ).json()
    client.patch(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}",
        json={"data": FULL_VACANCY_DATA},
    )
    client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}/status",
        json={"status": "active"},
    )
    return company, vacancy


def _submit(client, company_id: str, resume_id: str, vacancy_id: str, **extra):
    return client.post(
        "/api/v1/applications",
        headers={"X-Company-Id": company_id},
        json={"resume_id": resume_id, "vacancy_id": vacancy_id, **extra},
    )


def test_submit_creates_application_with_snapshots(client, db_session):
    resume_id = _publish_resume(client, "snap@cand.com")
    company, vacancy = _active_vacancy(client, "snap@emp.com")

    _auth_as(client, "snap@emp.com")
    response = _submit(client, company["id"], resume_id, vacancy["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "sent"
    assert body["resume_snapshot"]["desired_role"] == "Backend Developer"
    assert body["vacancy_snapshot"]["title"] == "Backend Developer"

    app_id = body["id"]
    resume = db_session.get(Resume, uuid.UUID(resume_id))
    resume.published_data = {"desired_role": "Changed"}
    db_session.commit()

    _auth_as(client, "snap@cand.com")
    detail = client.get(f"/api/v1/applications/{app_id}")
    assert detail.json()["resume_snapshot"]["desired_role"] == "Backend Developer"


def test_duplicate_submit_returns_400(client):
    resume_id = _publish_resume(client, "dup@cand.com")
    company, vacancy = _active_vacancy(client, "dup@emp.com")
    _auth_as(client, "dup@emp.com")
    assert _submit(client, company["id"], resume_id, vacancy["id"]).status_code == 201
    dup = _submit(client, company["id"], resume_id, vacancy["id"])
    assert dup.status_code == 400


def test_auto_reject_requires_confirmation(client):
    resume_id = _publish_resume(client, "auto@cand.com")
    client.patch(
        f"/api/v1/resumes/{resume_id}",
        json={
            "draft_data": {"salary_min": 500000},
            "auto_reject_settings": {
                "salary": {"enabled": True, "mode": "auto_reject"},
            },
        },
    )
    client.post(f"/api/v1/resumes/{resume_id}/publish")

    company, vacancy = _active_vacancy(client, "auto@emp.com")
    _auth_as(client, "auto@emp.com")

    blocked = _submit(client, company["id"], resume_id, vacancy["id"])
    assert blocked.status_code == 400

    accepted = _submit(
        client,
        company["id"],
        resume_id,
        vacancy["id"],
        confirm_auto_reject_risk=True,
    )
    assert accepted.status_code == 201
    assert accepted.json()["status"] == "auto_rejected"


def test_view_accept_creates_chat_and_close_readonly(client, db_session):
    resume_id = _publish_resume(client, "flow@cand.com")
    company, vacancy = _active_vacancy(client, "flow@emp.com")
    _auth_as(client, "flow@emp.com")
    app_id = _submit(client, company["id"], resume_id, vacancy["id"]).json()["id"]

    _auth_as(client, "flow@cand.com")
    assert client.post(f"/api/v1/applications/{app_id}/view").json()["status"] == "viewed"
    accepted = client.post(f"/api/v1/applications/{app_id}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert "chat_id" in accepted.json()

    closed = client.post(f"/api/v1/applications/{app_id}/close")
    assert closed.json()["status"] == "closed_after_acceptance"


def test_extend_once_and_expire_flow(client, db_session):
    resume_id = _publish_resume(client, "exp@cand.com")
    company, vacancy = _active_vacancy(client, "exp@emp.com")
    _auth_as(client, "exp@emp.com")
    app_id = _submit(client, company["id"], resume_id, vacancy["id"]).json()["id"]

    extended = client.post(
        f"/api/v1/applications/{app_id}/extend",
        headers={"X-Company-Id": company["id"]},
    )
    assert extended.status_code == 200

    again = client.post(
        f"/api/v1/applications/{app_id}/extend",
        headers={"X-Company-Id": company["id"]},
    )
    assert again.status_code == 400

    application = db_session.get(Application, uuid.UUID(app_id))
    application.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.commit()
    assert expire_due_applications(db_session) == 1

    _auth_as(client, "exp@cand.com")
    reactivation = client.post(f"/api/v1/applications/{app_id}/request-reactivation")
    assert reactivation.json()["status"] == "reactivation_requested"

    _auth_as(client, "exp@emp.com")
    confirmed = client.post(
        f"/api/v1/applications/{app_id}/confirm-reactivation",
        headers={"X-Company-Id": company["id"]},
    )
    assert confirmed.json()["status"] == "reactivated"


def test_limit_debit_on_submit(client, db_session):
    resume_id = _publish_resume(client, "lim@cand.com")
    company, vacancy = _active_vacancy(client, "lim@emp.com")
    company_row = db_session.get(Company, uuid.UUID(company["id"]))
    company_row.application_limit_monthly = 1
    company_row.applications_used_this_month = 0
    db_session.commit()

    _auth_as(client, "lim@emp.com")
    assert _submit(client, company["id"], resume_id, vacancy["id"]).status_code == 201

    resume_id2 = _publish_resume(client, "lim2@cand.com")
    _auth_as(client, "lim@emp.com")
    vacancy2 = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": {"title": "Second"}},
    ).json()
    client.patch(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy2['id']}",
        json={"data": {**FULL_VACANCY_DATA, "title": "Second role"}},
    )
    client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy2['id']}/status",
        json={"status": "active"},
    )
    blocked = _submit(client, company["id"], resume_id2, vacancy2["id"])
    assert blocked.status_code == 400
