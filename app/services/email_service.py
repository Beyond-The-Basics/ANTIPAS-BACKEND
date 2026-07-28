"""The email-sending seam.

`EmailVerificationService` depends on this protocol, never on Resend. Everything provider-specific
— HTTP, API keys, error shapes — lives below it in `app/core/resend.py`, so swapping providers or
faking delivery in tests is a matter of supplying a different implementation.
"""

import logging
from typing import Protocol

from app.core.config import settings
from app.core.resend import ResendClient
from app.models.enums import Locale
from app.services.email_templates import build_verification_email

logger = logging.getLogger(__name__)


class EmailService(Protocol):
    """What the domain layer is allowed to know about email: that it can be sent."""

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale: Locale) -> None: ...


class ResendEmailService:
    """Real delivery, backed by Resend."""

    def __init__(self, client: ResendClient) -> None:
        self._client = client

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale: Locale) -> None:
        subject, body = build_verification_email(
            otp=otp, minutes=settings.otp_ttl_minutes, locale=locale
        )
        await self._client.send(to=recipient_email, subject=subject, text=body)


class ConsoleEmailService:
    """Fallback when no `RESEND_API_KEY` is configured — local dev and tests.

    Logs that a send happened, never the code itself: dev logs get pasted into issues and shared
    terminals, and a live OTP is a credential. Tests that need the code override this dependency
    with their own recorder instead.
    """

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale: Locale) -> None:
        logger.info(
            "[email:stub] verification email for %s (locale=%s) — set RESEND_API_KEY to send for real",
            recipient_email,
            locale,
        )


def get_email_service() -> EmailService:
    """FastAPI dependency. Overridden in tests; falls back to the console stub when unconfigured."""
    if settings.resend_api_key:
        return ResendEmailService(ResendClient(settings.resend_api_key, settings.email_from))
    return ConsoleEmailService()
