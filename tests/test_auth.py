"""Email + password JWT auth."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

CREDS = {"name": "Alice", "email": "alice@example.com", "phone": "+15555550100", "password": "hunter2hunter2"}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def signup(client, **overrides) -> dict:
    resp = await client.post(SIGNUP, json={**CREDS, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- signup -------------------------------------------------------------------


async def test_signup_returns_token_and_user(client):
    body = await signup(client)
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_expire_minutes * 60
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["phone"] == "+15555550100"
    # Credentials must never come back out of the API.
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


async def test_signup_token_authenticates(client):
    body = await signup(client)
    resp = await client.get(ME, headers=bearer(body["access_token"]))
    assert resp.status_code == 200
    assert resp.json()["id"] == body["user"]["id"]


async def test_signup_rejects_duplicate_email_case_insensitively(client):
    await signup(client)
    resp = await client.post(SIGNUP, json={**CREDS, "email": "ALICE@example.com", "phone": "+15555550999"})
    assert resp.status_code == 409
    assert "email" in resp.json()["detail"].lower()


async def test_signup_rejects_duplicate_phone(client):
    await signup(client)
    resp = await client.post(SIGNUP, json={**CREDS, "email": "other@example.com"})
    assert resp.status_code == 409
    assert "phone" in resp.json()["detail"].lower()


@pytest.mark.parametrize(
    "field,value",
    [
        ("password", "short"),  # under the 8-char minimum
        ("password", "x" * 73),  # over bcrypt's 72-byte ceiling
        ("email", "not-an-email"),
        ("name", ""),
    ],
)
async def test_signup_validates_input(client, field, value):
    resp = await client.post(SIGNUP, json={**CREDS, field: value})
    assert resp.status_code == 422, resp.text


# --- login --------------------------------------------------------------------


async def test_login_succeeds_with_correct_password(client):
    created = await signup(client)
    resp = await client.post(LOGIN, json={"email": CREDS["email"], "password": CREDS["password"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["id"] == created["user"]["id"]


async def test_login_is_case_insensitive_on_email(client):
    await signup(client)
    resp = await client.post(LOGIN, json={"email": "ALICE@EXAMPLE.COM", "password": CREDS["password"]})
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "email,password",
    [
        ("alice@example.com", "wrongpassword"),
        ("nobody@example.com", "hunter2hunter2"),
    ],
)
async def test_login_rejects_bad_credentials_without_enumerating(client, email, password):
    """Wrong password and unknown account must be indistinguishable."""
    await signup(client)
    resp = await client.post(LOGIN, json={"email": email, "password": password})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password"


async def test_credential_less_user_cannot_log_in(client):
    """`POST /users` creates a user with no password_hash; login must reject, not crash."""
    resp = await client.post(
        "/api/v1/users", json={"name": "Bob", "phone": "+15555550200", "email": "bob@example.com"}
    )
    assert resp.status_code == 201
    resp = await client.post(LOGIN, json={"email": "bob@example.com", "password": "anything-at-all"})
    assert resp.status_code == 401


# --- token handling -----------------------------------------------------------


async def test_missing_token_is_401(client):
    resp = await client.get(ME)
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Bearer not.a.jwt"},
        {"Authorization": "Basic abc123"},  # wrong scheme
        {"Authorization": "Bearer "},  # empty token
    ],
)
async def test_malformed_tokens_are_401(client, header):
    resp = await client.get(ME, headers=header)
    assert resp.status_code == 401


async def test_expired_token_is_401(client):
    body = await signup(client)
    expired = jwt.encode(
        {
            "sub": body["user"]["id"],
            "type": "access",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get(ME, headers=bearer(expired))
    assert resp.status_code == 401


async def test_token_signed_with_another_key_is_401(client):
    body = await signup(client)
    forged = jwt.encode(
        {
            "sub": body["user"]["id"],
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        "not-the-real-signing-key",
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get(ME, headers=bearer(forged))
    assert resp.status_code == 401


async def test_non_access_token_is_rejected(client):
    """Guards a future refresh/reset token from being replayed as an access token."""
    body = await signup(client)
    refresh = jwt.encode(
        {
            "sub": body["user"]["id"],
            "type": "refresh",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get(ME, headers=bearer(refresh))
    assert resp.status_code == 401


async def test_token_for_deleted_user_is_401(client):
    """A valid signature naming a user who no longer exists must not authenticate."""
    token, _ = create_access_token(uuid.uuid4())
    resp = await client.get(ME, headers=bearer(token))
    assert resp.status_code == 401


# --- the dev stub -------------------------------------------------------------


async def test_stub_header_still_works_outside_production(client):
    """The X-User-Id fallback is what keeps local tooling and the rest of the suite working."""
    body = await signup(client)
    resp = await client.get(ME, headers={"X-User-Id": body["user"]["id"]})
    assert resp.status_code == 200
    assert resp.json()["id"] == body["user"]["id"]


async def test_bearer_token_wins_over_stub_header(client):
    """A real token must never be overridden by a spoofed id sent alongside it."""
    alice = await signup(client)
    bob = await signup(client, email="bob@example.com", phone="+15555550300", name="Bob")
    resp = await client.get(
        ME,
        headers={**bearer(alice["access_token"]), "X-User-Id": bob["user"]["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == alice["user"]["id"]


async def test_stub_header_is_ignored_in_production(client, monkeypatch):
    body = await signup(client)
    monkeypatch.setattr(settings, "environment", "production")
    resp = await client.get(ME, headers={"X-User-Id": body["user"]["id"]})
    assert resp.status_code == 401


async def test_bearer_token_still_works_in_production(client, monkeypatch):
    body = await signup(client)
    monkeypatch.setattr(settings, "environment", "production")
    resp = await client.get(ME, headers=bearer(body["access_token"]))
    assert resp.status_code == 200
