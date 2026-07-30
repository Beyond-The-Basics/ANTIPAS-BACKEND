"""One-time passcode generation, hashing, and comparison.

Deliberately separate from `security.py` (passwords, JWTs) because the threat model is different.
A 6-digit code has only a million possible values, so its safety comes from the policy around it —
short expiry, one active code per user, a hard cap on failed attempts — rather than from the code
itself being hard to guess.

Hashing still matters: a leaked `email_verifications` table must not hand out live codes. bcrypt
is used rather than a fast digest precisely because a million-value space is trivially enumerable
against SHA-256 but slow against a work-factored hash.
"""

import secrets

import bcrypt

OTP_DIGITS = 6
_OTP_SPACE = 10**OTP_DIGITS


def generate_otp() -> str:
    """A cryptographically secure numeric code, zero-padded to `OTP_DIGITS`.

    Padding rather than sampling from the 6-digit range keeps every code equally likely — drawing
    from 100000..999999 would silently exclude a tenth of the space.
    """
    return str(secrets.randbelow(_OTP_SPACE)).zfill(OTP_DIGITS)


def hash_otp(otp: str) -> str:
    return bcrypt.hashpw(otp.encode(), bcrypt.gensalt()).decode()


def verify_otp(plain: str, hashed: str | None) -> bool:
    """Constant-time compare via bcrypt. Returns False — never raises — on a malformed stored hash."""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False
