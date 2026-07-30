"""The email-sending seam.

`EmailVerificationService` depends on this protocol, never on a concrete provider. Everything
provider-specific — HTTP, API keys, error shapes — lives below it in `app/core/brevo.py` /
`app/core/resend.py`, so swapping providers or faking delivery in tests is a matter of supplying a
different implementation. Brevo is the provider the app sends through; Resend is kept as a second,
drop-in example of the same seam.
"""

import logging
from typing import Protocol

from app.core.brevo import BrevoClient
from app.core.config import settings
from app.core.resend import ResendClient
from app.models.enums import Locale
from app.services.email_templates import build_verification_email

logger = logging.getLogger(__name__)


class EmailService(Protocol):
    """What the domain layer is allowed to know about email: that it can be sent."""

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale: Locale) -> None: ...


class BrevoEmailService:
    """Real delivery, backed by Brevo."""

    def __init__(self, client: BrevoClient) -> None:
        self._client = client

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale: Locale) -> None:
        subject, body = build_verification_email(
            otp=otp, minutes=settings.otp_ttl_minutes, locale=locale
        )
        await self._client.send(to=recipient_email, subject=subject, text=body)


class ResendEmailService:
    """Real delivery, backed by Resend. Kept as a second implementation of the seam."""

    def __init__(self, client: ResendClient) -> None:
        self._client = client

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale: Locale) -> None:
        subject, body = build_verification_email(
            otp=otp, minutes=settings.otp_ttl_minutes, locale=locale
        )
        await self._client.send(to=recipient_email, subject=subject, text=body)


class ConsoleEmailService:
    """Fallback when no mail-provider key is configured — local dev and tests.

    Prints the code to the log so the flow is testable end to end without a mail provider. That
    matters more than it sounds: a provider's sandbox sender only delivers to the account owner's
    own address, so before a sender/domain is verified this is the *only* way to exercise signup
    with an arbitrary email.

    The code is a live credential, so printing it is gated on not being production — a prod deploy
    that forgot its API key must degrade to silence, not to leaking OTPs into a log aggregator.
    """

    async def send_verification_email(self, *, recipient_email: str, otp: str, locale: Locale) -> None:
        if settings.is_production:
            logger.error(
                "[email] no mail-provider key is set in production — verification email to %s was NOT sent",
                recipient_email,
            )
            return
        logger.warning(
            "[email:stub] verification code for %s (locale=%s): %s  "
            "— dev only; set BREVO_API_KEY to send for real",
            recipient_email,
            locale,
            otp,
        )


def get_email_service() -> EmailService:
    """FastAPI dependency. Overridden in tests; falls back to the console stub when unconfigured.

    Brevo is preferred; Resend is honored if only its key is present, so the seam keeps working
    either way.
    """
    if settings.brevo_api_key:
        return BrevoEmailService(BrevoClient(settings.brevo_api_key, settings.email_from))
    if settings.resend_api_key:
        return ResendEmailService(ResendClient(settings.resend_api_key, settings.email_from))
    return ConsoleEmailService()
