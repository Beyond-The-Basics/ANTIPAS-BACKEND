"""The provider edge for Brevo: what `BrevoEmailService` puts on the wire, and how failures map.

Uses `httpx.MockTransport`, so these run offline and need no API key. They pin the two things the
rest of the suite fakes away: that the email service really drives the client, and that every
provider failure surfaces as `EmailDeliveryError` rather than an httpx exception escaping into a
request handler. Mirrors `test_resend_client.py` for the active provider.
"""

import json

import httpx
import pytest

from app.core.brevo import BREVO_API_URL, BrevoClient, EmailDeliveryError, _parse_sender
from app.models.enums import Locale
from app.services.email_service import BrevoEmailService
from app.services.email_templates import SUBJECTS


def _service(handler) -> tuple[BrevoEmailService, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = BrevoClient("xkeysib-test-key", "Kickoff <no-reply@kickoff.test>", httpx.MockTransport(record))
    return BrevoEmailService(client), seen


async def test_service_sends_a_well_formed_request_to_brevo():
    service, seen = _service(lambda _r: httpx.Response(201, json={"messageId": "msg_123"}))
    await service.send_verification_email(
        recipient_email="player@example.com", otp="483921", locale=Locale.EN
    )

    assert len(seen) == 1
    request = seen[0]
    assert str(request.url) == BREVO_API_URL
    assert request.method == "POST"
    assert request.headers["api-key"] == "xkeysib-test-key"

    body = json.loads(request.content)
    assert body["sender"] == {"name": "Kickoff", "email": "no-reply@kickoff.test"}
    assert body["to"] == [{"email": "player@example.com"}]
    assert body["subject"] == SUBJECTS[Locale.EN]
    assert "483921" in body["textContent"]


async def test_service_sends_the_recipients_language():
    service, seen = _service(lambda _r: httpx.Response(201, json={"messageId": "msg_123"}))
    await service.send_verification_email(
        recipient_email="joueur@example.com", otp="483921", locale=Locale.FR
    )
    assert json.loads(seen[0].content)["subject"] == SUBJECTS[Locale.FR]


@pytest.mark.parametrize("status_code", [400, 401, 422, 429, 500, 503])
async def test_provider_error_responses_become_delivery_errors(status_code):
    service, _ = _service(
        lambda _r: httpx.Response(status_code, json={"message": "player@example.com is blocked"})
    )
    with pytest.raises(EmailDeliveryError) as exc:
        await service.send_verification_email(
            recipient_email="player@example.com", otp="483921", locale=Locale.EN
        )
    # Brevo's body can name the recipient and account state; none of it may reach the caller.
    assert "player@example.com" not in str(exc.value)


async def test_network_failures_become_delivery_errors():
    def blow_up(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    service, _ = _service(blow_up)
    with pytest.raises(EmailDeliveryError):
        await service.send_verification_email(
            recipient_email="player@example.com", otp="483921", locale=Locale.EN
        )


async def test_successful_send_returns_the_provider_message_id():
    client = BrevoClient(
        "xkeysib-test-key",
        "Kickoff <no-reply@kickoff.test>",
        httpx.MockTransport(lambda _r: httpx.Response(201, json={"messageId": "msg_abc"})),
    )
    assert await client.send(to="a@example.com", subject="s", text="t") == "msg_abc"


def test_parse_sender_handles_named_and_bare_addresses():
    assert _parse_sender("Kickoff <hi@example.com>") == {"name": "Kickoff", "email": "hi@example.com"}
    assert _parse_sender("  Spaced  < hi@example.com > ") == {"name": "Spaced", "email": "hi@example.com"}
    assert _parse_sender("bare@example.com") == {"name": "bare@example.com", "email": "bare@example.com"}
