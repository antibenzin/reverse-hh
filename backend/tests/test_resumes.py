import uuid
from datetime import UTC, datetime

from app.models.enums import ApplicationStatus


def _register(client, email: str, password: str = "password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def _login(client, email: str, password: str = "password123"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _auth_as(client, email: str, password: str = "password123"):
    client.cookies.clear()
    return _login(client, email, password)


def _create_profile(client, display_name: str = "Кандидат"):
    return client.post("/api/v1/candidate/profile", json={"display_name": display_name})


def _create_verified_company(client, email: str, name: str = "Employer Co"):
    _register(client, email)
    company = client.post(
        "/api/v1/companies",
        json={"name": name, "website": f"https://{email.split('@')[1]}", "tax_id": "7700000001"},
    ).json()
    client.post(f"/api/v1/companies/{company['id']}/verify")
    return company


def _resume_payload(**overrides):
    payload = {
        "draft_data": {
            "desired_role": "Backend Developer",
            "experience_mode": "has_experience",
            "city": "Москва",
            "skills": ["Python", "FastAPI"],
        },
        "contacts": [
            {"type": "email", "value": "private@example.com", "is_public": False},
            {"type": "telegram", "value": "@public_user", "is_public": True},
        ],
        "work_experiences": [
            {
                "company_name": "Secret Corp",
                "is_nda": True,
                "role": "Developer",
                "started_at": "2020-01-01",
                "ended_at": "2022-01-01",
                "description": "NDA project",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_create_update_publish_resume_flow(client):
    _register(client, "candidate@example.com")
    _create_profile(client)

    created = client.post("/api/v1/resumes", json={"title": "Python dev"})
    assert created.status_code == 201
    resume_id = created.json()["id"]
    assert created.json()["status"] == "draft"

    updated = client.patch(f"/api/v1/resumes/{resume_id}", json=_resume_payload())
    assert updated.status_code == 200
    assert len(updated.json()["draft_data"]["contacts"]) == 2

    published = client.post(f"/api/v1/resumes/{resume_id}/publish")
    assert published.status_code == 200
    body = published.json()
    assert body["status"] == "published"
    assert body["published_data"]["desired_role"] == "Backend Developer"


def test_hidden_resume_not_in_catalog(client):
    _register(client, "hidden@candidate.com")
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "Hidden"}).json()["id"]
    client.patch(
        f"/api/v1/resumes/{resume_id}",
        json={**_resume_payload(), "visibility": "hidden"},
    )
    client.post(f"/api/v1/resumes/{resume_id}/publish")

    company = _create_verified_company(client, "employer@hiddencorp.com")
    _auth_as(client, "employer@hiddencorp.com")

    catalog = client.get(
        "/api/v1/catalog/resumes",
        headers={"X-Company-Id": company["id"]},
    )
    assert catalog.status_code == 200
    assert catalog.json() == []


def test_hide_from_company_rule(client):
    _register(client, "hide@candidate.com")
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "Hide me"}).json()["id"]

    client.cookies.clear()
    company = _create_verified_company(client, "boss@hidecorp.com", name="Hide Corp")

    _auth_as(client, "hide@candidate.com")
    client.patch(
        f"/api/v1/resumes/{resume_id}",
        json=_resume_payload(
            visibility_rules=[{"rule_type": "hide_company_id", "rule_value": company["id"]}]
        ),
    )
    client.post(f"/api/v1/resumes/{resume_id}/publish")

    _auth_as(client, "boss@hidecorp.com")
    catalog = client.get(
        "/api/v1/catalog/resumes",
        headers={"X-Company-Id": company["id"]},
    )
    assert catalog.json() == []


def test_block_company_hides_resume(client):
    _register(client, "block@candidate.com")
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "Blocked"}).json()["id"]
    client.patch(f"/api/v1/resumes/{resume_id}", json=_resume_payload())
    client.post(f"/api/v1/resumes/{resume_id}/publish")

    company = _create_verified_company(client, "blocked@employer.com")
    _auth_as(client, "block@candidate.com")
    assert (
        client.post(
            f"/api/v1/resumes/{resume_id}/block-company",
            json={"company_id": company["id"]},
        ).status_code
        == 204
    )

    _auth_as(client, "blocked@employer.com")
    catalog = client.get(
        "/api/v1/catalog/resumes",
        headers={"X-Company-Id": company["id"]},
    )
    assert catalog.json() == []


def test_employer_sees_only_public_contacts_and_masks_nda(client, db_session):
    _register(client, "nda@candidate.com")
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "NDA resume"}).json()["id"]
    client.patch(
        f"/api/v1/resumes/{resume_id}",
        json=_resume_payload(draft_data={"desired_role": "Dev", "experience_mode": "nda"}),
    )
    client.post(f"/api/v1/resumes/{resume_id}/publish")

    company = _create_verified_company(client, "viewer@ndacorp.com")
    _auth_as(client, "viewer@ndacorp.com")

    detail = client.get(
        f"/api/v1/catalog/resumes/{resume_id}",
        headers={"X-Company-Id": company["id"]},
    )
    assert detail.status_code == 200
    contacts = detail.json()["published_data"]["contacts"]
    assert contacts == [{"type": "telegram", "value": "@public_user", "is_public": True}]
    experiences = detail.json()["published_data"]["work_experiences"]
    assert experiences[0]["company_name"] is None
    assert experiences[0]["is_nda"] is True


def test_link_only_resume_accessible_with_token(client):
    _register(client, "link@candidate.com")
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "Link only"}).json()["id"]
    client.patch(
        f"/api/v1/resumes/{resume_id}",
        json={**_resume_payload(), "visibility": "link_only"},
    )
    published = client.post(f"/api/v1/resumes/{resume_id}/publish").json()
    token = published["link_token"]

    company = _create_verified_company(client, "link@employer.com")
    _auth_as(client, "link@employer.com")

    assert (
        client.get(
            f"/api/v1/catalog/resumes/{resume_id}",
            headers={"X-Company-Id": company["id"]},
        ).status_code
        == 404
    )
    ok = client.get(
        f"/api/v1/catalog/resumes/{resume_id}",
        headers={"X-Company-Id": company["id"]},
        params={"token": token},
    )
    assert ok.status_code == 200


def test_archive_and_permanent_delete(client, db_session):
    from app.models import Application

    _register(client, "delete@candidate.com")
    _create_profile(client)
    resume_id = client.post("/api/v1/resumes", json={"title": "Delete me"}).json()["id"]
    client.patch(f"/api/v1/resumes/{resume_id}", json=_resume_payload())
    client.post(f"/api/v1/resumes/{resume_id}/publish")

    company = _create_verified_company(client, "del@employer.com")
    application = Application(
        resume_id=uuid.UUID(resume_id),
        vacancy_id=uuid.uuid4(),
        company_id=uuid.UUID(company["id"]),
        sent_by=uuid.uuid4(),
        status=ApplicationStatus.SENT,
        resume_snapshot={"desired_role": "Backend", "contacts": [{"value": "secret@mail.com"}]},
        vacancy_snapshot={"title": "Job"},
        expires_at=datetime.now(UTC),
        limit_debited=False,
    )
    db_session.add(application)
    db_session.commit()

    _auth_as(client, "delete@candidate.com")
    assert client.delete(f"/api/v1/resumes/{resume_id}").status_code == 204
    archived = client.get(f"/api/v1/resumes/{resume_id}")
    assert archived.json()["status"] == "archived"

    assert (
        client.delete(f"/api/v1/resumes/{resume_id}", params={"permanent": "true"}).status_code
        == 204
    )
    db_session.refresh(application)
    assert application.resume_snapshot["anonymized"] is True
    assert application.resume_snapshot["contacts"] == []
