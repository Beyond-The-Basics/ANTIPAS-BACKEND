"""The provider edge: what `ResendEmailService` actually puts on the wire, and how failures map.

Uses `httpx.MockTransport`, so these run offline and need no API key. They exist to pin the two
things the rest of the suite fakes away: that the email service really does drive the client, and
that every provider failure surfaces as `EmailDeliveryError` rather than an httpx exception
escaping into a request handler.
"""

import httpx
import pytest

from app.core.resend import RESEND_API_URL, EmailDeliveryError, ResendClient
from app.models.enums import Locale
from app.services.email_service import ResendEmailService
from app.services.email_templates import SUBJECTS


def _service(handler) -> tuple[ResendEmailService, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = ResendClient("re_test_key", "Kickoff <no-reply@kickoff.test>", httpx.MockTransport(record))
    return ResendEmailService(client), seen


async def test_service_sends_a_well_formed_request_to_resend():
    import json

    service, seen = _service(lambda _r: httpx.Response(200, json={"id": "msg_123"}))
    await service.send_verification_email(
        recipient_email="player@example.com", otp="483921", locale=Locale.EN
    )

    assert len(seen) == 1
    request = seen[0]
    assert str(request.url) == RESEND_API_URL
    assert request.method == "POST"
    assert request.headers["Authorization"] == "Bearer re_test_key"

    body = json.loads(request.content)
    assert body["from"] == "Kickoff <no-reply@kickoff.test>"
    assert body["to"] == ["player@example.com"]
    assert body["subject"] == SUBJECTS[Locale.EN]
    assert "483921" in body["text"]


async def test_service_sends_the_recipients_language():
    import json

    service, seen = _service(lambda _r: httpx.Response(200, json={"id": "msg_123"}))
    await service.send_verification_email(
        recipient_email="joueur@example.com", otp="483921", locale=Locale.FR
    )
    assert json.loads(seen[0].content)["subject"] == SUBJECTS[Locale.FR]


@pytest.mark.parametrize("status_code", [400, 401, 422, 429, 500, 503])
async def test_provider_error_responses_become_delivery_errors(status_code):
    service, _ = _service(
        lambda _r: httpx.Response(status_code, json={"message": "player@example.com is suppressed"})
    )
    with pytest.raises(EmailDeliveryError) as exc:
        await service.send_verification_email(
            recipient_email="player@example.com", otp="483921", locale=Locale.EN
        )
    # Resend's body names the recipient and account state; none of it may reach the caller.
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
    client = ResendClient(
        "re_test_key",
        "Kickoff <no-reply@kickoff.test>",
        httpx.MockTransport(lambda _r: httpx.Response(200, json={"id": "msg_abc"})),
    )
    assert await client.send(to="a@example.com", subject="s", text="t") == "msg_abc"


# --- console fallback ----------------------------------------------------------


async def test_console_stub_prints_the_code_outside_production(caplog, monkeypatch):
    """The only way to test signup with an arbitrary address before a domain is verified."""
    from app.core.config import settings
    from app.services.email_service import ConsoleEmailService

    monkeypatch.setattr(settings, "environment", "local")
    with caplog.at_level("WARNING"):
        await ConsoleEmailService().send_verification_email(
            recipient_email="dev@example.com", otp="483921", locale=Locale.EN
        )
    assert "483921" in caplog.text
    assert "dev@example.com" in caplog.text


async def test_console_stub_never_prints_the_code_in_production(caplog, monkeypatch):
    """A prod deploy missing its API key must go quiet, not leak live codes into the log."""
    from app.core.config import settings
    from app.services.email_service import ConsoleEmailService

    monkeypatch.setattr(settings, "environment", "production")
    with caplog.at_level("DEBUG"):
        await ConsoleEmailService().send_verification_email(
            recipient_email="user@example.com", otp="483921", locale=Locale.EN
        )
    assert "483921" not in caplog.text
    assert "NOT sent" in caplog.text
