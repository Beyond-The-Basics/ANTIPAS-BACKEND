"""Background tasks: listing expiry and the non-engagement credit refund.

These are stubs wired into Celery beat. The actual expiry/refund logic (per SPEC.md's Credits
section: refund a published search that expires with zero responses) will be implemented alongside
the service layer.
"""

from app.workers.celery_app import celery_app


@celery_app.task
def expire_stale_listings() -> dict[str, int]:
    """Mark OPEN listings past their expires_at as EXPIRED, and refund credits for searches that
    expired with zero engagement (per SPEC.md). Not yet implemented."""
    # TODO: implement against RosterSearch, OpponentSearch, GuestSearch, PlayerAvailability.
    return {"expired": 0, "refunded": 0}
