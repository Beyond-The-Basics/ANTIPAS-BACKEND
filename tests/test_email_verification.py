"""Email verification: OTP unit behaviour plus the full request → verify lifecycle.

Delivery is faked throughout by overriding `get_email_service`, which is the whole point of that
seam — no test reaches Resend, and the recorder hands back the code that would have been mailed so
assertions can act as the user reading their inbox.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.config import settings
from app.core.otp import OTP_DIGITS, generate_otp, hash_otp, verify_otp
from app.core.resend import EmailDeliveryError
from app.main import app
from app.models.email_verification import EmailVerification
from app.models.enums import Locale
from app.models.user import User
from app.services.email_service import get_email_service
from app.services.email_templates import SUBJECTS, build_verification_email
from tests.conftest import auth_header

# --- fakes --------------------------------------------------------------------


class RecordingEmailService:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale) -> None:
        self.sent.append({"to": recipient_email, "otp": otp, "locale": locale})

    @property
    def last_otp(self) -> str:
        return self.sent[-1]["otp"]


class BrokenEmailService:
    """Stands in for Resend being down."""

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale) -> None:
        raise EmailDeliveryError("provider unreachable")


@pytest_asyncio.fixture
async def mailbox(client):
    recorder = RecordingEmailService()
    app.dependency_overrides[get_email_service] = lambda: recorder
    return recorder


@pytest_asyncio.fixture
async def broken_mail(client):
    app.dependency_overrides[get_email_service] = lambda: BrokenEmailService()
    return None


async def signup(client, email: str = "player@example.com", phone: str = "+15556100001") -> dict:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"name": "Player", "email": email, "phone": phone, "password": "Passw0rd!"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["user"]


def wrong_code(actual: str) -> str:
    """A well-formed code guaranteed not to be `actual`."""
    return "000000" if actual != "000000" else "111111"


# --- unit: OTP ----------------------------------------------------------------


def test_generate_otp_is_always_six_digits():
    # Zero-padding is the point: sampling 100000..999999 would drop a tenth of the space.
    codes = {generate_otp() for _ in range(500)}
    assert all(len(c) == OTP_DIGITS and c.isdigit() for c in codes)
    assert len(codes) > 1, "generator returned a constant"


def test_hash_otp_round_trips_and_rejects_others():
    otp = "042931"
    hashed = hash_otp(otp)
    assert hashed != otp, "raw code must never be the stored value"
    assert verify_otp(otp, hashed)
    assert not verify_otp("042930", hashed)


def test_hash_otp_is_salted():
    assert hash_otp("123456") != hash_otp("123456")


def test_verify_otp_survives_missing_or_malformed_hash():
    assert not verify_otp("123456", None)
    assert not verify_otp("123456", "not-a-bcrypt-digest")


def test_verification_email_is_localized():
    for locale in (Locale.EN, Locale.FR, Locale.AR):
        subject, body = build_verification_email(otp="483921", minutes=10, locale=locale)
        assert subject == SUBJECTS[locale]
        assert "483921" in body and "10" in body
    # Distinct copy per language, not the English body three times.
    bodies = {build_verification_email(otp="1", minutes=10, locale=loc)[1] for loc in Locale}
    assert len(bodies) == len(Locale)


# --- integration --------------------------------------------------------------


async def test_signup_sends_a_verification_email(client, mailbox):
    user = await signup(client)
    assert user["email_verified"] is False
    assert len(mailbox.sent) == 1
    assert mailbox.sent[0]["to"] == "player@example.com"


async def test_verify_with_the_right_code_marks_the_address_verified(client, db_session, mailbox):
    user = await signup(client)

    resp = await client.post(
        "/api/v1/verification/email/verify",
        json={"otp": mailbox.last_otp},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["email_verified"] is True

    await db_session.refresh(await db_session.get(User, user["id"]))
    assert (await db_session.get(User, user["id"])).email_verified is True
    # The challenge is destroyed on success, so the same code can't be replayed.
    assert await db_session.scalar(select(EmailVerification)) is None


async def test_wrong_code_counts_attempts_and_the_cap_destroys_the_challenge(
    client, db_session, mailbox
):
    user = await signup(client)
    bad = wrong_code(mailbox.last_otp)
    headers = auth_header(user["id"])

    for expected_attempts in range(1, settings.otp_max_attempts):
        resp = await client.post(
            "/api/v1/verification/email/verify", json={"otp": bad}, headers=headers
        )
        assert resp.status_code == 400
        record = await db_session.scalar(select(EmailVerification))
        await db_session.refresh(record)
        assert record.attempts == expected_attempts

    # The final permitted attempt burns the challenge outright.
    resp = await client.post("/api/v1/verification/email/verify", json={"otp": bad}, headers=headers)
    assert resp.status_code == 400
    assert await db_session.scalar(select(EmailVerification)) is None

    # ...so even the genuine code is now worthless.
    resp = await client.post(
        "/api/v1/verification/email/verify", json={"otp": mailbox.last_otp}, headers=headers
    )
    assert resp.status_code == 400
    assert (await db_session.get(User, user["id"])).email_verified is False


async def test_expired_code_is_rejected_and_cleared(client, db_session, mailbox):
    user = await signup(client)
    record = await db_session.scalar(select(EmailVerification))
    record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/verification/email/verify",
        json={"otp": mailbox.last_otp},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()
    assert await db_session.scalar(select(EmailVerification)) is None


async def test_verifying_without_an_outstanding_code_fails(client, mailbox):
    user = await signup(client)
    # Consume the challenge, then try again with nothing outstanding.
    await client.post(
        "/api/v1/verification/email/verify",
        json={"otp": mailbox.last_otp},
        headers=auth_header(user["id"]),
    )
    # Re-verifying an already-verified address is a no-op success, so use a second, unverified user.
    other = await signup(client, email="other@example.com", phone="+15556100002")
    record_owner = auth_header(other["id"])
    await client.post("/api/v1/verification/email/verify", json={"otp": "000000"}, headers=record_owner)

    resp = await client.post(
        "/api/v1/verification/email/verify", json={"otp": "999999"}, headers=record_owner
    )
    assert resp.status_code == 400


async def test_resend_replaces_the_previous_code(client, db_session, mailbox, monkeypatch):
    user = await signup(client)
    first_otp = mailbox.last_otp
    first_hash = (await db_session.scalar(select(EmailVerification))).otp_hash

    # Step past the resend floor rather than sleeping through it.
    monkeypatch.setattr(settings, "otp_resend_interval_seconds", 0)
    resp = await client.post(
        "/api/v1/verification/email/resend", headers=auth_header(user["id"])
    )
    assert resp.status_code == 202, resp.text

    assert len(mailbox.sent) == 2
    records = (await db_session.scalars(select(EmailVerification))).all()
    assert len(records) == 1, "only one live challenge per user"
    await db_session.refresh(records[0])
    assert records[0].otp_hash != first_hash

    # The superseded code no longer works.
    if mailbox.last_otp != first_otp:
        resp = await client.post(
            "/api/v1/verification/email/verify",
            json={"otp": first_otp},
            headers=auth_header(user["id"]),
        )
        assert resp.status_code == 400


async def test_requesting_again_too_soon_is_rate_limited(client, mailbox):
    user = await signup(client)  # signup already issued one, moments ago

    resp = await client.post("/api/v1/verification/email/request", headers=auth_header(user["id"]))
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") is not None
    assert len(mailbox.sent) == 1, "rate-limited request must not send"


async def test_requesting_when_already_verified_succeeds_without_sending(client, mailbox):
    user = await signup(client)
    await client.post(
        "/api/v1/verification/email/verify",
        json={"otp": mailbox.last_otp},
        headers=auth_header(user["id"]),
    )
    sent_before = len(mailbox.sent)

    resp = await client.post("/api/v1/verification/email/request", headers=auth_header(user["id"]))
    assert resp.status_code == 202
    assert resp.json()["email_verified"] is True
    assert len(mailbox.sent) == sent_before


async def test_changing_the_email_resets_verification_and_re_sends(client, db_session, mailbox):
    user = await signup(client)
    await client.post(
        "/api/v1/verification/email/verify",
        json={"otp": mailbox.last_otp},
        headers=auth_header(user["id"]),
    )
    assert (await db_session.get(User, user["id"])).email_verified is True
    sent_before = len(mailbox.sent)

    resp = await client.patch(
        "/api/v1/users/me",
        json={"email": "moved@example.com"},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "moved@example.com"
    assert resp.json()["email_verified"] is False

    assert len(mailbox.sent) == sent_before + 1
    assert mailbox.sent[-1]["to"] == "moved@example.com"

    # The new code verifies the new address.
    resp = await client.post(
        "/api/v1/verification/email/verify",
        json={"otp": mailbox.last_otp},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 200
    assert (await db_session.get(User, user["id"])).email_verified is True


async def test_email_change_cannot_collide_with_another_account_by_case(client, mailbox):
    await signup(client, email="taken@example.com", phone="+15556100003")
    mover = await signup(client, email="mover@example.com", phone="+15556100004")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"email": "TAKEN@Example.com"},
        headers=auth_header(mover["id"]),
    )
    assert resp.status_code == 409


async def test_email_change_is_stored_normalized(client, db_session, mailbox):
    user = await signup(client)
    resp = await client.patch(
        "/api/v1/users/me",
        json={"email": "  MiXeD@Example.COM  "},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "mixed@example.com"
    # The code has to be addressed to the stored form, not the raw input.
    assert mailbox.sent[-1]["to"] == "mixed@example.com"


async def test_a_code_mailed_to_the_old_address_cannot_verify_the_new_one(
    client, db_session, mailbox
):
    user = await signup(client)
    stale_otp = mailbox.last_otp

    # Move the address directly, leaving the in-flight challenge pointing at the old one.
    record = await db_session.scalar(select(EmailVerification))
    account = await db_session.get(User, user["id"])
    account.email = "elsewhere@example.com"
    await db_session.commit()
    assert record.email != account.email

    resp = await client.post(
        "/api/v1/verification/email/verify",
        json={"otp": stale_otp},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 400
    assert (await db_session.get(User, user["id"])).email_verified is False


@pytest.mark.parametrize("bad", ["12345", "1234567", "abcdef", "12 345", ""])
async def test_malformed_codes_are_rejected_before_reaching_the_service(client, mailbox, bad):
    user = await signup(client)
    resp = await client.post(
        "/api/v1/verification/email/verify", json={"otp": bad}, headers=auth_header(user["id"])
    )
    assert resp.status_code == 422


# --- provider failure ---------------------------------------------------------


async def test_signup_still_succeeds_when_the_provider_is_down(client, db_session, broken_mail):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Player",
            "email": "unlucky@example.com",
            "phone": "+15556100009",
            "password": "Passw0rd!",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["email_verified"] is False
    # No half-written challenge left behind by the rolled-back send.
    assert await db_session.scalar(select(EmailVerification)) is None


async def test_request_reports_a_provider_failure_without_leaking_details(
    client, db_session, broken_mail
):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Player",
            "email": "unlucky2@example.com",
            "phone": "+15556100010",
            "password": "Passw0rd!",
        },
    )
    user = resp.json()["user"]

    resp = await client.post("/api/v1/verification/email/request", headers=auth_header(user["id"]))
    assert resp.status_code == 502
    assert "provider" not in resp.json()["detail"].lower()
    assert await db_session.scalar(select(EmailVerification)) is None
