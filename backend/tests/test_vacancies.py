from tests.test_companies import _create_company, _register
from tests.test_resumes import _auth_as

FULL_VACANCY_DATA = {
    "title": "Backend Developer",
    "salary_min": 200000,
    "salary_max": 300000,
    "currency": "RUB",
    "work_format": "remote",
    "city": "Москва",
    "country": "Россия",
    "employment_type": "full_time",
    "responsibilities": "Build APIs",
    "requirements": "Python experience",
    "hiring_stages": "Interview",
    "sender_name": "HR",
    "sender_role": "Recruiter",
}


def _invite_recruiter(client, company_id: str, email: str) -> None:
    invite = client.post(
        f"/api/v1/companies/{company_id}/members",
        json={"email": email},
    )
    token = invite.json()["token"]
    client.cookies.clear()
    _register(client, email)
    client.post("/api/v1/companies/invites/accept", json={"token": token})


def test_owner_sees_all_vacancies_recruiter_sees_assigned_only(client):
    _register(client, "owner@vac.com")
    company = _create_company(client, "Vac Co").json()
    owner_vacancy = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": {"title": "Owner vacancy"}},
    ).json()

    _invite_recruiter(client, company["id"], "recruiter@vac.com")
    _auth_as(client, "owner@vac.com")
    assigned = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": {"title": "Shared vacancy"}},
    ).json()
    members = client.get(f"/api/v1/companies/{company['id']}/members").json()
    recruiter_id = next(m["user_id"] for m in members if m["email"] == "recruiter@vac.com")
    client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{assigned['id']}/recruiters",
        json={"recruiter_ids": [recruiter_id]},
    )

    _auth_as(client, "recruiter@vac.com")
    recruiter_vacancy = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": {"title": "Recruiter own"}},
    ).json()

    listing = client.get(f"/api/v1/companies/{company['id']}/vacancies")
    ids = {item["id"] for item in listing.json()}
    assert owner_vacancy["id"] not in ids
    assert assigned["id"] in ids
    assert recruiter_vacancy["id"] in ids

    _auth_as(client, "owner@vac.com")
    owner_listing = client.get(f"/api/v1/companies/{company['id']}/vacancies")
    assert len(owner_listing.json()) == 3


def test_recruiter_cannot_change_vacancy_status(client):
    _register(client, "boss@status.com")
    company = _create_company(client, "Status Co").json()
    vacancy = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": FULL_VACANCY_DATA},
    ).json()

    _invite_recruiter(client, company["id"], "rec@status.com")
    _auth_as(client, "boss@status.com")
    members = client.get(f"/api/v1/companies/{company['id']}/members").json()
    recruiter_id = next(m["user_id"] for m in members if m["email"] == "rec@status.com")
    client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}/recruiters",
        json={"recruiter_ids": [recruiter_id]},
    )

    _auth_as(client, "rec@status.com")
    denied = client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}/status",
        json={"status": "active"},
    )
    assert denied.status_code == 403


def test_active_status_requires_mandatory_fields(client):
    _register(client, "salary@owner.com")
    company = _create_company(client, "Salary Co").json()
    vacancy = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": {"title": "Incomplete"}},
    ).json()

    fail = client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}/status",
        json={"status": "active"},
    )
    assert fail.status_code == 400

    client.patch(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}",
        json={"data": FULL_VACANCY_DATA},
    )
    ok = client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}/status",
        json={"status": "active"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "active"


def test_assign_recruiters_adds_users(client):
    _register(client, "assign@owner.com")
    company = _create_company(client, "Assign Co").json()
    vacancy = client.post(
        f"/api/v1/companies/{company['id']}/vacancies",
        json={"data": {"title": "Team hire"}},
    ).json()

    _invite_recruiter(client, company["id"], "hire@assign.com")
    _auth_as(client, "assign@owner.com")
    members = client.get(f"/api/v1/companies/{company['id']}/members").json()
    recruiter_id = next(m["user_id"] for m in members if m["email"] == "hire@assign.com")

    updated = client.post(
        f"/api/v1/companies/{company['id']}/vacancies/{vacancy['id']}/recruiters",
        json={"recruiter_ids": [recruiter_id]},
    )
    assert updated.status_code == 200
    assert recruiter_id in updated.json()["recruiter_ids"]
