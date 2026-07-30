"""The enforcement gate: an unverified account can authenticate but cannot use the product.

Signup and login issue a token on purpose (a returning user has to be able to sign in and finish
verifying), but every feature endpoint hangs off `get_verified_user` and turns an unverified caller
away with 403. This walks that end to end: signup → blocked → verify → allowed.
"""

import pytest
import pytest_asyncio

from app.main import app
from app.services.email_service import get_email_service


class RecordingEmailService:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale) -> None:
        self.sent.append({"to": recipient_email, "otp": otp, "locale": locale})

    @property
    def last_otp(self) -> str:
        return self.sent[-1]["otp"]


@pytest_asyncio.fixture
async def mailbox(client):
    recorder = RecordingEmailService()
    app.dependency_overrides[get_email_service] = lambda: recorder
    return recorder


async def _signup(client, email="player@example.com", phone="+15556200001") -> dict:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"name": "Player", "email": email, "phone": phone, "password": "Passw0rd!"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_unverified_user_is_blocked_from_features_then_allowed_after_verifying(client, mailbox):
    body = await _signup(client)
    token = body["access_token"]
    assert body["user"]["email_verified"] is False

    # A feature endpoint is off-limits while unverified.
    blocked = await client.post("/api/v1/teams", json={"name": "Falcons", "sport": "soccer"}, headers=_bearer(token))
    assert blocked.status_code == 403, blocked.text

    # The routes needed to *become* verified stay reachable with the same token.
    assert (await client.get("/api/v1/auth/me", headers=_bearer(token))).status_code == 200

    verify = await client.post(
        "/api/v1/verification/email/verify", json={"otp": mailbox.last_otp}, headers=_bearer(token)
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["email_verified"] is True

    # Same token, same request — now it goes through.
    allowed = await client.post("/api/v1/teams", json={"name": "Falcons", "sport": "soccer"}, headers=_bearer(token))
    assert allowed.status_code == 201, allowed.text


async def test_login_still_issues_a_token_to_an_unverified_user(client, mailbox):
    """Blocking is at the feature layer, not login — otherwise a returning user could never verify."""
    await _signup(client, email="return@example.com", phone="+15556200002")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "return@example.com", "password": "Passw0rd!"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]
    assert resp.json()["user"]["email_verified"] is False
