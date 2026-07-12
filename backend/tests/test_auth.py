def test_me_without_cookie_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_register_duplicate_email_returns_400(client):
    payload = {"email": "bob@example.com", "password": "password123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"


def test_login_with_valid_credentials(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "password123"},
    )
    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json() == {"ok": True}
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "carol@example.com"


def test_login_with_invalid_password_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "dave@example.com", "password": "password123"},
    )
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_logout_clears_session(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "password123"},
    )
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    set_cookie = logout.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401


def test_register_then_me_returns_user(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert register.status_code == 201
    user_id = register.json()["id"]

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        "id": user_id,
        "email": "alice@example.com",
        "display_name": "",
        "is_admin": False,
        "has_candidate_profile": False,
        "companies": [],
    }


def test_create_candidate_profile_requires_auth(client):
    response = client.post(
        "/api/v1/candidate/profile",
        json={"display_name": "Иван"},
    )
    assert response.status_code == 401


def test_create_candidate_profile(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "profile@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/v1/candidate/profile",
        json={"display_name": "Иван Иванов"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["display_name"] == "Иван Иванов"
    assert "id" in body

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Иван Иванов"
    assert me.json()["has_candidate_profile"] is True


def test_create_duplicate_candidate_profile_returns_400(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "dup-profile@example.com", "password": "password123"},
    )
    assert (
        client.post("/api/v1/candidate/profile", json={"display_name": "First"}).status_code
        == 201
    )
    duplicate = client.post("/api/v1/candidate/profile", json={"display_name": "Second"})
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Candidate profile already exists"


def test_update_candidate_profile(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "update@example.com", "password": "password123"},
    )
    client.post("/api/v1/candidate/profile", json={"display_name": "Старое имя"})

    response = client.patch(
        "/api/v1/candidate/profile",
        json={"display_name": "Новое имя"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Новое имя"

    me = client.get("/api/v1/auth/me")
    assert me.json()["display_name"] == "Новое имя"


def test_update_candidate_profile_without_profile_returns_404(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "no-profile@example.com", "password": "password123"},
    )
    response = client.patch(
        "/api/v1/candidate/profile",
        json={"display_name": "Имя"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate profile not found"


def test_me_returns_company_memberships(client, db_session):
    import uuid

    from app.models import Company, CompanyMember, User
    from app.models.enums import CompanyMemberRole

    register = client.post(
        "/api/v1/auth/register",
        json={"email": "member@example.com", "password": "password123"},
    )
    user = db_session.get(User, uuid.UUID(register.json()["id"]))

    company_a = Company(name="Acme Corp")
    company_b = Company(name="Beta Inc")
    db_session.add_all([company_a, company_b])
    db_session.flush()
    db_session.add_all(
        [
            CompanyMember(
                company_id=company_a.id,
                user_id=user.id,
                role=CompanyMemberRole.OWNER,
            ),
            CompanyMember(
                company_id=company_b.id,
                user_id=user.id,
                role=CompanyMemberRole.RECRUITER,
            ),
        ]
    )
    db_session.commit()

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    companies = me.json()["companies"]
    assert len(companies) == 2
    by_name = {c["company_name"]: c for c in companies}
    assert by_name["Acme Corp"]["role"] == "owner"
    assert by_name["Beta Inc"]["role"] == "recruiter"
