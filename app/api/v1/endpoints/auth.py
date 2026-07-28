"""Email + password auth.

Signup and login both return the same `TokenResponse`, so a client can treat them identically:
store the token, use the embedded user, move on. There is no refresh token — see
`app/core/security.py` for why and what that costs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, normalize_email, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.schemas.user import UserRead
from app.services import email_verification_service
from app.services.email_service import EmailService, get_email_service

router = APIRouter()


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserRead.model_validate(user))


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    data: SignupRequest,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> TokenResponse:
    """Create an account and sign it in.

    Phone is required and unique alongside email, so both are checked before insert — a 409 naming
    the field beats a raw unique-violation 500.

    A verification code goes out on the way, best-effort: the account is already committed, and
    refusing to register someone because the mail provider is down would be the worse failure. An
    unverified account can ask for a new code at `POST /verification/email/resend`.
    """
    email = normalize_email(data.email)
    phone = data.phone.strip()

    if await db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if await db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Phone already registered")

    user = User(
        name=data.name.strip(),
        email=email,
        phone=phone,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await email_verification_service.send_verification_code_best_effort(db, user, email_service)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Exchange email + password for an access token.

    An unknown email and a wrong password return the same 401 on purpose: distinguishing them
    turns this endpoint into an account-enumeration oracle.
    """
    user = await db.scalar(select(User).where(func.lower(User.email) == normalize_email(data.email)))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _token_response(user)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    """Resolve the caller's token to their profile — how a client validates a stored token."""
    return current_user
