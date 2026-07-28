"""Background tasks: listing expiry, the non-engagement credit refund, and OTP cleanup.

The listing/refund task is still a stub wired into Celery beat. The actual expiry/refund logic
(per SPEC.md's Credits section: refund a published search that expires with zero responses) will
be implemented alongside the service layer.
"""

import asyncio

from app.db.session import async_session_factory
from app.services import email_verification_service
from app.workers.celery_app import celery_app


@celery_app.task
def expire_stale_listings() -> dict[str, int]:
    """Mark OPEN listings past their expires_at as EXPIRED, and refund credits for searches that
    expired with zero engagement (per SPEC.md). Not yet implemented."""
    # TODO: implement against RosterSearch, OpponentSearch, GuestSearch, PlayerAvailability.
    return {"expired": 0, "refunded": 0}


@celery_app.task
def purge_expired_email_verifications() -> dict[str, int]:
    """Drop spent verification challenges.

    Expired rows are already refused by `verify_code`, so this is hygiene rather than
    enforcement — it stops the table growing without bound from codes nobody ever used, and keeps
    dead bcrypt digests from lingering in backups.
    """

    async def _run() -> int:
        async with async_session_factory() as db:
            return await email_verification_service.purge_expired(db)

    return {"purged": asyncio.run(_run())}
