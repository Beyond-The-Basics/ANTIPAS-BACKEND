"""Request/response models for the email-verification endpoints."""

from pydantic import BaseModel, Field

from app.core.otp import OTP_DIGITS


class VerifyEmailRequest(BaseModel):
    # Pattern rather than `int` so leading zeros survive — "042931" is a valid code.
    otp: str = Field(pattern=rf"^\d{{{OTP_DIGITS}}}$")


class VerificationStatus(BaseModel):
    """Uniform reply for every endpoint here, so a client reads one shape.

    Carries no hint about whether a code exists, when it expires, or how many attempts are left:
    all of that is inferable by an attacker who only controls the email field.
    """

    email_verified: bool
    detail: str
