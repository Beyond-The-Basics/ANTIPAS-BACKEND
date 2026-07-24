"""Shared FastAPI dependencies.

`get_current_user` is the single seam for authentication. It now resolves a **JWT bearer token**
issued by `POST /auth/login` or `POST /auth/signup`.

Outside production it *also* accepts the legacy `X-User-Id` stub header, which trusts the caller
completely. That fallback is what lets the test suite and local tooling act as any user without a
password; `settings.is_production` disables it, and it is only ever consulted when no
`Authorization` header was sent. `get_current_user_via_firebase` remains ready for the eventual
phone/OTP migration — swapping the alias at the bottom is still the whole change.
"""

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.firebase import verify_id_token
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User

_UNAUTHORIZED = "Not authenticated"


async def _user_or_401(db: AsyncSession, user_id: uuid.UUID) -> User:
    """A token can outlive the user it names — a deleted account must not stay authenticated."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _UNAUTHORIZED)
    return user


async def get_current_user_via_jwt(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_id: uuid.UUID | None = Header(default=None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve `Authorization: Bearer <jwt>` to its `User`.

    Falls back to the `X-User-Id` stub outside production when no bearer token was supplied.
    """
    if authorization is None:
        if x_user_id is not None and not settings.is_production:
            return await _user_or_401(db, x_user_id)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            _UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Expected 'Authorization: Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return await _user_or_401(db, user_id)


async def get_current_user_stub(
    x_user_id: uuid.UUID = Header(..., alias="X-User-Id", description="STUB AUTH: id of the acting user"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Pre-auth seam: trusts the caller's claimed id outright. Kept for local tooling and reference."""
    return await _user_or_401(db, x_user_id)


async def get_current_user_via_firebase(
    authorization: str = Header(..., alias="Authorization", description="Bearer <firebase-id-token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Real phone/OTP auth: verify the Firebase ID token and resolve it to a User. Ready to swap in."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Expected 'Authorization: Bearer <token>'")
    try:
        claims = verify_id_token(token)
    except Exception as exc:  # firebase raises various token errors
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Firebase token") from exc

    firebase_uid = claims["uid"]
    user = await db.scalar(select(User).where(User.firebase_uid == firebase_uid))
    if user is None:
        # First request from a client whose phone already exists as a User: link the uid.
        phone = claims.get("phone_number")
        if phone:
            user = await db.scalar(select(User).where(User.phone == phone))
            if user is not None:
                user.firebase_uid = firebase_uid
                await db.commit()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No account linked to this identity")
    return user


# Active authentication dependency. Swap the right-hand side to go live with Firebase.
get_current_user = get_current_user_via_jwt


async def require_non_production() -> None:
    """Guard for endpoints that bypass authentication and must never be reachable in production."""
    if settings.is_production:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
