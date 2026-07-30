"""Brevo transactional-email client.

Mirrors `resend.py`: a thin wrapper around one third-party provider so nothing above this file
imports the provider's shape. Callers talk to `EmailService` (`app/services/email_service.py`);
this is the provider the app sends through in every environment that has a `BREVO_API_KEY`.

Uses `httpx.AsyncClient` rather than an SDK — a blocking HTTP call inside a request handler would
stall the event loop for every other in-flight request.

Raises the same `EmailDeliveryError` the domain layer already catches, so swapping Resend for Brevo
changed nothing above the seam.
"""

import logging
import re

import httpx

from app.core.resend import EmailDeliveryError

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
_TIMEOUT_SECONDS = 10.0

# Splits a `"Display Name <addr@host>"` sender into its parts. Brevo wants a structured
# `{name, email}` object, unlike Resend which takes the combined string verbatim.
_SENDER_RE = re.compile(r"^\s*(?P<name>.*?)\s*<\s*(?P<email>[^>]+?)\s*>\s*$")


def _parse_sender(sender: str) -> dict[str, str]:
    """Turn `EMAIL_FROM` into Brevo's `{name, email}` shape.

    Accepts either `"Kickoff <hi@example.com>"` or a bare `"hi@example.com"`.
    """
    match = _SENDER_RE.match(sender)
    if match:
        return {"name": match.group("name") or match.group("email"), "email": match.group("email")}
    addr = sender.strip()
    return {"name": addr, "email": addr}


class BrevoClient:
    def __init__(
        self, api_key: str, sender: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._api_key = api_key
        self._sender = _parse_sender(sender)
        # Tests pass an `httpx.MockTransport` to assert on the request this builds without a
        # network call or an API key; production leaves it None and gets httpx's default.
        self._transport = transport

    async def send(self, *, to: str, subject: str, text: str) -> str:
        """Send one transactional email. Returns Brevo's message id; raises `EmailDeliveryError`."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.post(
                    BREVO_API_URL,
                    headers={"api-key": self._api_key, "accept": "application/json"},
                    json={
                        "sender": self._sender,
                        "to": [{"email": to}],
                        "subject": subject,
                        "textContent": text,
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("Brevo request failed: %s", exc)
            raise EmailDeliveryError("Email provider unreachable") from exc

        if response.is_error:
            logger.warning("Brevo rejected the message (%s): %s", response.status_code, response.text)
            raise EmailDeliveryError("Email provider rejected the message")

        return response.json().get("messageId", "")
