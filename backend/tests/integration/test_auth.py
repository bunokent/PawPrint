"""Integration: auth endpoints (register/login/logout/me + Google OAuth 2.0)."""


import pytest

from apps.users.dto import GoogleProfile
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_register_creates_user_and_session(api_client):
    resp = api_client.post(
        "/api/auth/register",
        {"email": "New@Example.com", "password": "supersecret1", "display_name": "New User"},
        format="json",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["display_name"] == "New User"
    # session cookie issued
    assert "sessionid" in resp.cookies


def test_register_duplicate_email_400(api_client):
    UserFactory(email="taken@example.com")
    resp = api_client.post(
        "/api/auth/register", {"email": "taken@example.com", "password": "supersecret1"}, format="json"
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "auth_error"


def test_register_weak_password_400(api_client):
    resp = api_client.post(
        "/api/auth/register", {"email": "weak@example.com", "password": "short"}, format="json"
    )
    assert resp.status_code == 400


def test_login_logout_me_flow(api_client):
    UserFactory(email="mia@example.com")
    resp = api_client.post(
        "/api/auth/login", {"email": "mia@example.com", "password": "testpass123"}, format="json"
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "mia@example.com"
    me = api_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "mia@example.com"
    out = api_client.post("/api/auth/logout")
    assert out.status_code == 200
    me2 = api_client.get("/api/auth/me")
    assert me2.status_code == 401
    assert me2.json()["error"]["session_expired"] is True


def test_login_wrong_password_400(api_client):
    UserFactory(email="mia@example.com")
    resp = api_client.post(
        "/api/auth/login", {"email": "mia@example.com", "password": "wrong-password"}, format="json"
    )
    assert resp.status_code == 400


def test_me_guest_401(api_client):
    resp = api_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_auth_write_throttle_20_per_min(api_client):
    for i in range(20):
        resp = api_client.post(
            "/api/auth/login", {"email": f"x{i}@example.com", "password": "nope-nope"}, format="json"
        )
        assert resp.status_code == 400
    resp = api_client.post(
        "/api/auth/login", {"email": "over@example.com", "password": "nope-nope"}, format="json"
    )
    assert resp.status_code == 429


def test_google_url_returns_consent_url(api_client):
    resp = api_client.post(
        "/api/auth/google/url", {"redirect_uri": "http://localhost:5173/auth/callback"}, format="json"
    )
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=" in url and "redirect_uri=" in url


def test_google_callback_registers_new_gmail_user(api_client, monkeypatch):
    profile = GoogleProfile(
        sub="g-123", email="gmail.user@gmail.com", email_verified=True, name="Gmail User", picture=""
    )
    monkeypatch.setattr("apps.users.services._exchange_google_code", lambda code, redirect_uri: profile)
    resp = api_client.post(
        "/api/auth/google/callback",
        {"code": "fake-code", "redirect_uri": "http://localhost:5173/auth/callback"},
        format="json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] is True
    assert body["user"]["email"] == "gmail.user@gmail.com"
    assert body["user"]["google_id"] == "g-123"
    assert body["user"]["email_verified"] is True
    # SocialAccount recorded via allauth
    from allauth.socialaccount.models import SocialAccount

    assert SocialAccount.objects.filter(provider="google", uid="g-123").exists()
    # session established
    assert api_client.get("/api/auth/me").status_code == 200


def test_google_callback_links_existing_email_account(api_client, monkeypatch):
    existing = UserFactory(email="linked@example.com")
    profile = GoogleProfile(
        sub="g-999", email="linked@example.com", email_verified=True, name="", picture=""
    )
    monkeypatch.setattr("apps.users.services._exchange_google_code", lambda code, redirect_uri: profile)
    resp = api_client.post(
        "/api/auth/google/callback",
        {"code": "fake", "redirect_uri": "http://localhost:5173/auth/callback"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["created"] is False
    existing.refresh_from_db()
    assert existing.google_id == "g-999"


def test_google_callback_existing_google_signin(api_client, monkeypatch):
    user = UserFactory(email="repeat@gmail.com", google_id="g-555", email_verified=True)
    profile = GoogleProfile(
        sub="g-555", email="repeat@gmail.com", email_verified=True, name="Repeat", picture=""
    )
    monkeypatch.setattr("apps.users.services._exchange_google_code", lambda code, redirect_uri: profile)
    resp = api_client.post(
        "/api/auth/google/callback",
        {"code": "fake", "redirect_uri": "http://localhost:5173/auth/callback"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["created"] is False
    assert resp.json()["user"]["id"] == str(user.pk)


def test_google_callback_exchange_failure_400(api_client, monkeypatch):
    import httpx

    def boom(code, redirect_uri):
        raise httpx.HTTPStatusError("bad", request=None, response=None)  # type: ignore[arg-type]

    monkeypatch.setattr("apps.users.services._exchange_google_code", boom)
    resp = api_client.post(
        "/api/auth/google/callback",
        {"code": "bad", "redirect_uri": "http://localhost:5173/auth/callback"},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "oauth_error"
