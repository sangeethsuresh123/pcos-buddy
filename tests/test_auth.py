from urllib.parse import unquote

import sqlite3

from fastapi.testclient import TestClient

from backend.app import app
from backend.auth import google
from backend.config import settings

CREDS = {"email": "alice@example.com", "password": "supersecret1"}


def test_register_creates_user_and_session(anon_client):
    res = anon_client.post("/api/auth/register", json=CREDS)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "alice@example.com"
    assert "password" not in body and "password_hash" not in body
    assert "set-cookie" in res.headers
    assert anon_client.get("/api/auth/me").json()["email"] == "alice@example.com"


def test_register_normalizes_and_rejects_bad_input(anon_client):
    anon_client.post("/api/auth/register", json=CREDS)
    assert anon_client.post("/api/auth/register", json=CREDS).status_code == 409
    assert anon_client.post(
        "/api/auth/register", json={"email": "not-an-email", "password": "longenough1"}
    ).status_code == 422
    assert anon_client.post(
        "/api/auth/register", json={"email": "bob@example.com", "password": "short"}
    ).status_code == 422


def test_login_and_logout(anon_client):
    anon_client.post("/api/auth/register", json=CREDS)
    anon_client.post("/api/auth/logout")
    assert anon_client.get("/api/auth/me").status_code == 401

    assert anon_client.post(
        "/api/auth/login", json={**CREDS, "password": "wrongpassword"}
    ).status_code == 401
    assert anon_client.post("/api/auth/login", json=CREDS).status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 200


def test_protected_routes_require_auth(anon_client):
    for path in ("/api/weight/entries", "/api/weight/analytics"):
        assert anon_client.get(path).status_code == 401
    assert anon_client.post("/api/ml/predict", json={}).status_code == 401
    assert anon_client.get("/api/chat/sessions").status_code == 401


def test_health_and_auth_endpoints_are_open(anon_client):
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 401


def test_bearer_token_authentication(anon_client):
    res = anon_client.post("/api/auth/register", json=CREDS)
    token = res.cookies.get("pcos_session")
    assert token
    anon_client.cookies.clear()
    headers = {"Authorization": f"Bearer {token}"}
    assert anon_client.get("/api/auth/me", headers=headers).status_code == 200


def test_weight_data_is_isolated_per_user(anon_client):
    with TestClient(app) as alice:
        alice.post("/api/auth/register", json={"email": "alice@example.com", "password": "password111"})
        alice.post("/api/weight/entries", json={"date": "2026-01-10", "weight_kg": 70})
        assert len(alice.get("/api/weight/entries").json()) == 1

    with TestClient(app) as bob:
        bob.post("/api/auth/register", json={"email": "bob@example.com", "password": "password222"})
        assert bob.get("/api/weight/entries").json() == []
        bob.post("/api/weight/entries", json={"date": "2026-01-10", "weight_kg": 92})

    with TestClient(app) as alice2:
        alice2.post("/api/auth/login", json={"email": "alice@example.com", "password": "password111"})
        entries = alice2.get("/api/weight/entries").json()
        assert len(entries) == 1
        assert entries[0]["weight_kg"] == 70


GOOGLE_REDIRECT = "http://oauth.example:8000/api/auth/google/callback"


def _enable_google(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "cid.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    monkeypatch.setattr(settings, "google_redirect_uri", GOOGLE_REDIRECT)


def _fake_google(monkeypatch, email="guser@example.com", sub="google-sub-1", verified=True):
    async def exchange(code):
        assert code == "auth-code"
        assert google.redirect_uri() == GOOGLE_REDIRECT
        return {"access_token": "token"}

    async def userinfo(access_token):
        assert access_token == "token"
        return {"email": email, "sub": sub, "email_verified": verified}

    monkeypatch.setattr(google, "exchange_code", exchange)
    monkeypatch.setattr(google, "fetch_userinfo", userinfo)


def _set_oauth_cookies(client, state="state-123", next_path="/"):
    client.cookies.set("pcos_oauth_state", state)
    client.cookies.set("pcos_oauth_next", next_path)


def test_auth_config_disabled_when_not_configured(anon_client, monkeypatch):
    for attr in ("google_client_id", "google_client_secret", "google_redirect_uri"):
        monkeypatch.setattr(settings, attr, "")
    res = anon_client.get("/api/auth/config")
    assert res.status_code == 200
    assert res.json() == {"google_enabled": False, "google_login_url": None}


def test_auth_config_reports_host_independent_login_url(anon_client, monkeypatch):
    _enable_google(monkeypatch)
    res = anon_client.get("/api/auth/config")
    assert res.status_code == 200
    body = res.json()
    assert body["google_enabled"] is True
    assert body["google_login_url"] == "http://oauth.example:8000/api/auth/google/login"


def test_google_login_disabled_returns_503(anon_client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")
    monkeypatch.setattr(settings, "google_redirect_uri", "")
    res = anon_client.get("/api/auth/google/login", follow_redirects=False)
    assert res.status_code == 503


def test_google_login_uses_pinned_redirect_uri(anon_client, monkeypatch):
    _enable_google(monkeypatch)
    res = anon_client.get(
        "/api/auth/google/login?redirect=/weight", follow_redirects=False
    )
    assert res.status_code == 302
    location = res.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=cid.apps.googleusercontent.com" in location
    assert "redirect_uri=http%3A%2F%2Foauth.example%3A8000%2Fapi%2Fauth%2Fgoogle%2Fcallback" in location
    assert anon_client.cookies.get("pcos_oauth_state")
    assert unquote(anon_client.cookies.get("pcos_oauth_next")) == "/weight"


def test_google_callback_creates_user_and_session(anon_client, monkeypatch):
    _enable_google(monkeypatch)
    _fake_google(monkeypatch)
    _set_oauth_cookies(anon_client, next_path="/weight")
    res = anon_client.get(
        "/api/auth/google/callback?code=auth-code&state=state-123",
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"] == "/weight"
    me = anon_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "guser@example.com"


def test_google_callback_rejects_bad_state(anon_client, monkeypatch):
    _enable_google(monkeypatch)
    _fake_google(monkeypatch)
    _set_oauth_cookies(anon_client)
    res = anon_client.get(
        "/api/auth/google/callback?code=auth-code&state=WRONG",
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"].startswith("/login?error=google")
    assert "state_mismatch" in res.headers["location"]


def test_google_callback_rejects_unverified_email(anon_client, monkeypatch):
    _enable_google(monkeypatch)
    _fake_google(monkeypatch, verified=False)
    _set_oauth_cookies(anon_client)
    res = anon_client.get(
        "/api/auth/google/callback?code=auth-code&state=state-123",
        follow_redirects=False,
    )
    assert res.headers["location"].startswith("/login?error=google")
    assert "invalid_userinfo" in res.headers["location"]


def test_google_links_existing_password_account(anon_client, monkeypatch):
    reg = anon_client.post(
        "/api/auth/register",
        json={"email": "link@example.com", "password": "password123"},
    )
    user_id = reg.json()["id"]
    anon_client.post("/api/auth/logout")

    _enable_google(monkeypatch)
    _fake_google(monkeypatch, email="link@example.com", sub="google-sub-9")
    _set_oauth_cookies(anon_client)
    anon_client.get(
        "/api/auth/google/callback?code=auth-code&state=state-123",
        follow_redirects=False,
    )
    assert anon_client.get("/api/auth/me").json()["id"] == user_id

    anon_client.post("/api/auth/logout")
    assert anon_client.post(
        "/api/auth/login", json={"email": "link@example.com", "password": "password123"}
    ).status_code == 200


def test_google_only_user_cannot_password_login(anon_client, monkeypatch):
    _enable_google(monkeypatch)
    _fake_google(monkeypatch, email="nopass@example.com", sub="google-sub-2")
    _set_oauth_cookies(anon_client)
    anon_client.get(
        "/api/auth/google/callback?code=auth-code&state=state-123",
        follow_redirects=False,
    )
    anon_client.post("/api/auth/logout")
    assert anon_client.post(
        "/api/auth/login", json={"email": "nopass@example.com", "password": "password123"}
    ).status_code == 401

    _set_oauth_cookies(anon_client, state="state-456")
    anon_client.get(
        "/api/auth/google/callback?code=auth-code&state=state-456",
        follow_redirects=False,
    )
    assert anon_client.get("/api/auth/me").status_code == 200


def test_migrates_legacy_auth_db_without_google_id(tmp_path, monkeypatch, anon_client):
    db_path = tmp_path / "auth.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        "CREATE TABLE users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT NOT NULL UNIQUE, "
        "password_hash TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now')));"
        "CREATE TABLE sessions ("
        "token_hash TEXT PRIMARY KEY, "
        "user_id INTEGER NOT NULL, "
        "expires_at TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now')));"
    )
    conn.execute(
        "INSERT INTO users (email, password_hash) VALUES ('legacy@example.com', 'not-a-real-hash')"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(settings, "auth_db_path", str(db_path))
    assert anon_client.get("/api/auth/me").status_code == 401

    _enable_google(monkeypatch)
    _fake_google(monkeypatch, email="new@example.com", sub="google-sub-77")
    _set_oauth_cookies(anon_client)
    res = anon_client.get(
        "/api/auth/google/callback?code=auth-code&state=state-123",
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"] == "/"
    assert anon_client.get("/api/auth/me").json()["email"] == "new@example.com"