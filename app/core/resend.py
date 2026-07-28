"""Resend transactional-email client.

Mirrors `firebase.py`: a thin wrapper around one third-party provider so nothing above this file
imports the provider's shape. Callers talk to `EmailService`
(`app/services/email_service.py`); replacing Resend means writing a new client plus a new
`EmailService` implementation and changing nothing else.

Uses `httpx.AsyncClient` rather than the official SDK, which is synchronous — a blocking HTTP call
inside a request handler would stall the event loop for every other in-flight request.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
_TIMEOUT_SECONDS = 10.0


class EmailDeliveryError(Exception):
    """Sending failed.

    Carries no provider detail on purpose: the message reaches an API response, and Resend's error
    bodies echo the recipient address and account state. Diagnostics go to the log instead.
    """


class ResendClient:
    def __init__(
        self, api_key: str, sender: str, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._api_key = api_key
        self._sender = sender
        # Tests pass an `httpx.MockTransport` to assert on the request this builds without a
        # network call or an API key; production leaves it None and gets httpx's default.
        self._transport = transport

    async def send(self, *, to: str, subject: str, text: str) -> str:
        """Send one transactional email. Returns Resend's message id; raises `EmailDeliveryError`."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, transport=self._transport) as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"from": self._sender, "to": [to], "subject": subject, "text": text},
                )
        except httpx.HTTPError as exc:
            logger.warning("Resend request failed: %s", exc)
            raise EmailDeliveryError("Email provider unreachable") from exc

        if response.is_error:
            logger.warning("Resend rejected the message (%s): %s", response.status_code, response.text)
            raise EmailDeliveryError("Email provider rejected the message")

        return response.json().get("id", "")
