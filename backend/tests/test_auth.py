def test_me_without_cookie_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_register_duplicate_email_returns_400(client):
    payload = {
        "email": "bob@example.com",
        "password": "password123",
        "display_name": "Bob",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"


def test_login_with_valid_credentials(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "carol@example.com",
            "password": "password123",
            "display_name": "Carol",
        },
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
        json={
            "email": "dave@example.com",
            "password": "password123",
            "display_name": "Dave",
        },
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
        json={
            "email": "eve@example.com",
            "password": "password123",
            "display_name": "Eve",
        },
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
        json={
            "email": "alice@example.com",
            "password": "password123",
            "display_name": "Alice",
        },
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
