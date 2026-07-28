"""Password hashing and JWT issue/verify.

This is the *credential* layer behind `POST /auth/signup` and `POST /auth/login`. The auth **seam**
— how an arbitrary request resolves to a `User` — stays in `app/api/deps.py`; this module only knows
how to turn a password into a hash and a user id into a signed token.

Tokens are bearer access tokens with no refresh counterpart: signing in issues one long-lived token
and signing out discards it client-side. That is the deliberate "JWT first" shape — it means there
is no server-side revocation, so a leaked token is valid until it expires.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt hashes at most 72 bytes and silently ignores everything past that, which would make two
# different long passwords interchangeable. Schemas reject longer input rather than truncate it.
MAX_PASSWORD_BYTES = 72

TOKEN_TYPE = "access"


class TokenError(Exception):
    """A token that can't be trusted: expired, malformed, wrong signature, or wrong type."""


def normalize_email(email: str) -> str:
    """Fold an address to its stored form.

    Email is the login identifier, so every path that writes or looks one up has to agree on
    casing — signup, login, and the profile's email change. Comparing raw input against the column
    lets `FOO@x.com` slip past a uniqueness check that `foo@x.com` would have failed, which with
    email verification in play means two accounts can end up owning one verified address.
    """
    return email.strip().lower()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    """Returns False — never raises — when the user has no password set.

    Dev-created users (`POST /users`) have a null `password_hash`; they must fail the password
    check like any wrong password rather than blowing up the login endpoint.
    """
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False  # hash column holds something that isn't a bcrypt digest


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Sign an access token for `user_id`. Returns `(token, expires_in_seconds)`."""
    expires_in = settings.access_token_expire_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID:
    """Verify `token` and return the user id it names. Raises `TokenError` on anything suspect."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    # Guards against a future refresh/reset token being replayed as an access token.
    if payload.get("type") != TOKEN_TYPE:
        raise TokenError("Not an access token")

    try:
        return uuid.UUID(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise TokenError("Token subject is not a user id") from exc
