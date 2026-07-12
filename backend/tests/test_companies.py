import uuid


def _register(client, email: str, password: str = "password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def _create_company(client, name: str, **kwargs):
    payload = {"name": name, **kwargs}
    return client.post("/api/v1/companies", json=payload)


def test_create_company_makes_user_owner(client):
    _register(client, "owner@acme.com")
    response = _create_company(
        client,
        "Acme Corp",
        website="https://acme.com",
        tax_id="1234567890",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme Corp"
    assert body["my_role"] == "owner"
    assert body["requires_manual_review"] is False


def test_second_company_requires_manual_review(client):
    _register(client, "multi@corp.com")
    _create_company(client, "First Co")
    second = _create_company(client, "Second Co")
    assert second.status_code == 201
    assert second.json()["requires_manual_review"] is True


def test_recruiter_cannot_invite_members(client):
    _register(client, "owner@invite.com")
    company = _create_company(client, "Invite Co").json()

    invite = client.post(
        f"/api/v1/companies/{company['id']}/members",
        json={"email": "recruiter@invite.com"},
    )
    assert invite.status_code == 201
    token = invite.json()["token"]

    client.cookies.clear()
    _register(client, "recruiter@invite.com")
    assert client.post("/api/v1/companies/invites/accept", json={"token": token}).status_code == 200

    blocked = client.post(
        f"/api/v1/companies/{company['id']}/members",
        json={"email": "another@invite.com"},
    )
    assert blocked.status_code == 403


def test_owner_can_invite_and_recipient_accepts(client):
    _register(client, "boss@team.com")
    company = _create_company(client, "Team LLC").json()

    invite = client.post(
        f"/api/v1/companies/{company['id']}/members",
        json={"email": "hire@team.com"},
    )
    assert invite.status_code == 201
    token = invite.json()["token"]

    client.cookies.clear()
    _register(client, "hire@team.com")
    accept = client.post("/api/v1/companies/invites/accept", json={"token": token})
    assert accept.status_code == 200

    me = client.get("/api/v1/auth/me")
    assert len(me.json()["companies"]) == 1
    assert me.json()["companies"][0]["role"] == "recruiter"


def test_join_request_flow(client):
    _register(client, "founder@join.com")
    company = _create_company(client, "Join Co").json()

    client.cookies.clear()
    _register(client, "applicant@join.com")
    request = client.post(f"/api/v1/companies/{company['id']}/join-requests")
    assert request.status_code == 201
    request_id = request.json()["id"]

    client.cookies.clear()
    client.post(
        "/api/v1/auth/login",
        json={"email": "founder@join.com", "password": "password123"},
    )
    approve = client.post(
        f"/api/v1/companies/{company['id']}/join-requests/{request_id}/approve"
    )
    assert approve.status_code == 200
    assert approve.json()["role"] == "recruiter"


def test_verification_auto_approves_matching_domain(client):
    _register(client, "admin@matchcorp.com")
    company = _create_company(
        client,
        "Match Corp",
        website="https://matchcorp.com",
        tax_id="7700000000",
    ).json()

    verify = client.post(f"/api/v1/companies/{company['id']}/verify")
    assert verify.status_code == 202
    assert verify.json()["verification_status"] == "verified"


def test_verification_stays_pending_for_manual_review_company(client):
    _register(client, "user@manual.com")
    _create_company(
        client,
        "First",
        website="https://first.com",
        tax_id="111",
    )
    second = _create_company(
        client,
        "Second",
        website="https://manual.com",
        tax_id="222",
    ).json()

    verify = client.post(f"/api/v1/companies/{second['id']}/verify")
    assert verify.status_code == 202
    assert verify.json()["verification_status"] == "pending"
    assert verify.json()["requires_manual_review"] is True


def test_workspace_header_requires_membership(client):
    _register(client, "outsider@example.com")
    company_id = str(uuid.uuid4())
    response = client.get(
        "/api/v1/companies/workspace/me",
        headers={"X-Company-Id": company_id},
    )
    assert response.status_code == 403


def test_workspace_header_returns_membership(client):
    _register(client, "member@workspace.com")
    company = _create_company(client, "Workspace Co").json()

    response = client.get(
        "/api/v1/companies/workspace/me",
        headers={"X-Company-Id": company["id"]},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "owner"


def test_owner_can_archive_company(client):
    _register(client, "archive@co.com")
    company = _create_company(client, "Archive Co").json()

    archive = client.post(f"/api/v1/companies/{company['id']}/archive")
    assert archive.status_code == 204

    listing = client.get("/api/v1/companies")
    assert listing.json() == []
