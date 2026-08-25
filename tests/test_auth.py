from tests.conftest import register_and_login, auth_headers


def test_register_creates_account(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "a@test.com", "password": "TestPass123", "name": "A"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "a@test.com"
    assert body["is_faculty"] is False
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dup@test.com", "password": "TestPass123", "name": "A"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400, resp.text


def test_login_success_returns_token(client):
    register_and_login(client, email="login@test.com")  # asserts 200/201 internally


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/auth/register",
        json={"email": "wp@test.com", "password": "TestPass123", "name": "A"},
    )
    resp = client.post(
        "/api/auth/login", json={"email": "wp@test.com", "password": "WrongPass456"}
    )
    assert resp.status_code == 401, resp.text


def test_auth_required_routes_reject_missing_token(client):
    assert client.get("/api/profile/me").status_code == 401
    assert client.get("/api/ideas").status_code == 401
    assert client.get("/api/faculty/dashboard").status_code == 401


def test_profile_me_round_trips_authenticated(client):
    token = register_and_login(client, email="me@test.com")
    resp = client.get("/api/profile/me", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"
