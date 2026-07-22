"""Shared FastAPI dependencies.

`get_current_user` is the single seam for authentication. It is currently a **stub** that trusts an
`X-User-Id` header — good enough to build and exercise authorization logic without a Firebase project.
To switch to real auth, replace the alias at the bottom of this file with
`get_current_user = get_current_user_via_firebase`; route signatures don't change.
"""

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.firebase import verify_id_token
from app.db.session import get_db
from app.models.user import User


async def get_current_user_stub(
    x_user_id: uuid.UUID = Header(
        ..., alias="X-User-Id", description="STUB AUTH: id of the acting user"
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.get(User, x_user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown or missing X-User-Id")
    return user


async def get_current_user_via_firebase(
    authorization: str = Header(..., alias="Authorization", description="Bearer <firebase-id-token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Real auth: verify the Firebase ID token and resolve it to a User. Ready to swap in."""
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
get_current_user = get_current_user_stub
