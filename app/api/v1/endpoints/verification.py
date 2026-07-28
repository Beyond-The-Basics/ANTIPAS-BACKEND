"""Email verification: request a code, submit a code.

Thin over `email_verification_service`, like every other router here. `request` and `resend` are
the same operation — the spec names both, and a client that has just registered says "request"
while one staring at a code entry box says "resend" — so they share a handler rather than drifting
apart.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.verification import VerificationStatus, VerifyEmailRequest
from app.services import email_verification_service
from app.services.email_service import EmailService, get_email_service

router = APIRouter(prefix="/verification/email", tags=["verification"])

_SENT = "Verification code sent"
_ALREADY = "Email already verified"
_VERIFIED = "Email verified"


async def _issue_code(
    current_user: User, db: AsyncSession, email_service: EmailService
) -> VerificationStatus:
    if current_user.email_verified:
        # Not an error: re-requesting after verifying is a harmless client race, and a 4xx here
        # would push clients into special-casing a success.
        return VerificationStatus(email_verified=True, detail=_ALREADY)
    await email_verification_service.send_verification_code(db, current_user, email_service)
    return VerificationStatus(email_verified=False, detail=_SENT)


@router.post("/request", response_model=VerificationStatus, status_code=status.HTTP_202_ACCEPTED)
async def request_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> VerificationStatus:
    """Send a code to the caller's address, replacing any already outstanding."""
    return await _issue_code(current_user, db, email_service)


@router.post("/resend", response_model=VerificationStatus, status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> VerificationStatus:
    """Alias of `/request` — same rate limit, same invalidation of the previous code."""
    return await _issue_code(current_user, db, email_service)


@router.post("/verify", response_model=VerificationStatus)
async def verify_email(
    data: VerifyEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VerificationStatus:
    """Consume a code. On success the address is verified and the challenge is destroyed."""
    await email_verification_service.verify_code(db, current_user, data.otp)
    return VerificationStatus(email_verified=True, detail=_VERIFIED)
