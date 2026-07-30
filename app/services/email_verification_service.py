"""Email-verification domain logic: issue a code, check a code, reset on email change.

Talks to `EmailService`, never to Resend. The invariants it maintains:

* one live code per user — enforced by the unique `user_id` in `email_verifications`, with each
  new request deleting the previous row;
* codes expire (`settings.otp_ttl_minutes`) and die after
  `settings.otp_max_attempts` wrong guesses;
* a new code can't be requested more often than `settings.otp_resend_interval_seconds`.

The resend floor is derived from the live row's `created_at` rather than from Redis. That keeps
the rule in the same transaction as the thing it guards — no second store to get out of sync, and
it survives a worker restart — at the cost of the window resetting once a code is consumed or
burned through. That's the right trade here: the limit exists to stop mail-bombing an address, and
both of those paths already required either the real code or five wrong ones.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.otp import generate_otp, hash_otp, verify_otp
from app.core.resend import EmailDeliveryError
from app.models.email_verification import EmailVerification
from app.models.user import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

ALREADY_VERIFIED = "Email already verified"
NO_EMAIL = "This account has no email address to verify"
NO_ACTIVE_CODE = "No verification is in progress — request a new code"
EXPIRED = "That code has expired — request a new one"
INVALID = "Incorrect code"
TOO_MANY_ATTEMPTS = "Too many incorrect attempts — request a new code"
SEND_FAILED = "Could not send the verification email — please try again shortly"


async def _active_verification(db: AsyncSession, user_id: uuid.UUID) -> EmailVerification | None:
    return await db.scalar(select(EmailVerification).where(EmailVerification.user_id == user_id))


async def _clear_verification(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(EmailVerification).where(EmailVerification.user_id == user_id))


def _retry_after(existing: EmailVerification, now: datetime) -> int:
    """Whole seconds left on the resend floor, or 0 once it has elapsed."""
    elapsed = (now - existing.created_at).total_seconds()
    return max(0, int(settings.otp_resend_interval_seconds - elapsed))


async def send_verification_code(
    db: AsyncSession, user: User, email_service: EmailService, *, enforce_rate_limit: bool = True
) -> None:
    """Issue a fresh code and email it, replacing any code already outstanding.

    No-ops when the address is already verified, so a client can call this without first checking.
    `enforce_rate_limit=False` is for flows the user didn't trigger by asking for a code — signup
    and an email change — where a floor inherited from the previous address would be wrong.

    The new row is flushed but not committed until the provider has accepted the message: if
    sending fails, the rollback restores the *previous* code, which is still the one in the user's
    inbox and still the one that should work.
    """
    if user.email is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, NO_EMAIL)
    if user.email_verified:
        return

    now = datetime.now(UTC)
    existing = await _active_verification(db, user.id)
    if enforce_rate_limit and existing is not None:
        retry_after = _retry_after(existing, now)
        if retry_after > 0:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Please wait {retry_after}s before requesting another code",
                headers={"Retry-After": str(retry_after)},
            )

    await _clear_verification(db, user.id)
    otp = generate_otp()
    db.add(
        EmailVerification(
            user_id=user.id,
            email=user.email,
            otp_hash=hash_otp(otp),
            expires_at=now + timedelta(minutes=settings.otp_ttl_minutes),
        )
    )
    await db.flush()

    try:
        await email_service.send_verification_email(
            recipient_email=user.email, otp=otp, locale=user.locale
        )
    except EmailDeliveryError as exc:
        await db.rollback()
        # `rollback()` expires every instance in the session, so any later attribute read on `user`
        # would fire a lazy reload — from Pydantic's synchronous serializer, in signup's case,
        # which blows up with MissingGreenlet instead of returning the account that was just
        # created. Reloading it here keeps the object usable for whoever called us.
        await db.refresh(user)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, SEND_FAILED) from exc

    await db.commit()


async def send_verification_code_best_effort(
    db: AsyncSession, user: User, email_service: EmailService
) -> None:
    """Same, but never lets a mail failure break the caller.

    Signup and email changes have already succeeded by the time the code goes out; failing those
    requests because Resend is down would be a worse outcome than an unverified address the user
    can fix from the resend endpoint.

    Callers **must** have committed their own work first. The failure path here rolls back, and a
    rollback can only safely discard the half-written challenge — not the signup or address change
    that prompted it.
    """
    try:
        await send_verification_code(db, user, email_service, enforce_rate_limit=False)
    except HTTPException:
        logger.warning("Verification email could not be sent to user %s", user.id)


async def verify_code(db: AsyncSession, user: User, otp: str) -> None:
    """Check `otp` against the live challenge; on success mark the address verified.

    Every failure path that consumes the challenge deletes it, so a caller can never keep guessing
    against a row that has already been spent.
    """
    if user.email_verified:
        return

    record = await _active_verification(db, user.id)
    if record is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, NO_ACTIVE_CODE)

    # The address moved while this code was in flight; it can only ever verify what it was sent to.
    if record.email != user.email:
        await _clear_verification(db, user.id)
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, NO_ACTIVE_CODE)

    if record.expires_at <= datetime.now(UTC):
        await _clear_verification(db, user.id)
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, EXPIRED)

    if not verify_otp(otp, record.otp_hash):
        record.attempts += 1
        exhausted = record.attempts >= settings.otp_max_attempts
        if exhausted:
            await _clear_verification(db, user.id)
        await db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, TOO_MANY_ATTEMPTS if exhausted else INVALID
        )

    user.email_verified = True
    await _clear_verification(db, user.id)
    await db.commit()


async def reset_for_new_email(
    db: AsyncSession, user: User, new_email: str, email_service: EmailService
) -> None:
    """Point the account at `new_email`, drop its verified status, and send a code to the new one.

    Callers must have already checked that `new_email` isn't taken.

    The address change is committed *before* the code goes out, deliberately: sending rolls back on
    failure, and an unreachable mail provider must not silently undo the user's edit. Worst case
    they end up on the new address, unverified, with the resend endpoint one tap away.
    """
    user.email = new_email
    user.email_verified = False
    await _clear_verification(db, user.id)
    await db.commit()
    await send_verification_code_best_effort(db, user, email_service)


async def purge_expired(db: AsyncSession) -> int:
    """Delete every challenge past its expiry. Returns how many went."""
    result = await db.execute(
        delete(EmailVerification).where(EmailVerification.expires_at <= datetime.now(UTC))
    )
    await db.commit()
    return result.rowcount or 0
