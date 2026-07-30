import logging

from fastapi import FastAPI

from app.admin import setup_admin
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def _check_email_config() -> None:
    """Warn loudly when the mail setup will silently fail to deliver.

    A provider (Brevo) accepts the API call and *then* rejects an unvalidated sender asynchronously,
    so a bad `EMAIL_FROM` produces a 2xx with no local error — verification emails just never arrive.
    The placeholder default is guaranteed to hit that, so surface it at startup rather than leaving it
    to be discovered one un-received code at a time.
    """
    has_provider = bool(settings.brevo_api_key or settings.resend_api_key)
    placeholder = "example.com" in settings.email_from
    if has_provider and placeholder:
        logger.warning(
            "EMAIL_FROM is the placeholder %r but a mail provider is configured — the provider will "
            "accept the request and then reject delivery from an unvalidated sender. Set EMAIL_FROM to "
            "an address validated in your provider account.",
            settings.email_from,
        )
    elif not has_provider:
        logger.warning(
            "No mail provider key set (BREVO_API_KEY/RESEND_API_KEY) — verification codes will be "
            "logged to the console instead of emailed. Fine for local dev; set a key to send for real."
        )


app = FastAPI(title="Kickoff App API", version="0.1.0")

app.include_router(api_router, prefix=settings.api_v1_prefix)

setup_admin(app)
_check_email_config()


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "kickoff-api", "docs": "/docs"}
