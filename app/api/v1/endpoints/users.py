import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_non_production
from app.core.security import normalize_email
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import email_verification_service
from app.services.email_service import EmailService, get_email_service

router = APIRouter()


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_non_production)],
)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Create a profile with **no credential** — dev and test tooling only, hence the 404 in
    production. `POST /auth/signup` is the real path; a user created here has a null
    `password_hash` and cannot log in until one is set."""
    if await db.scalar(select(User).where(User.phone == data.phone)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Phone already registered")
    if data.email and await db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(name=data.name, phone=data.phone, email=data.email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> User:
    """Partial update. Also used by the onboarding wizard to save each step as the user goes, so a
    refresh mid-wizard doesn't lose progress — see `POST /users/me/onboarding/complete` for the
    flag that marks the whole thing done."""
    # Changing the address un-verifies the account and re-issues a code; deferred to the end so it
    # commits after the rest of the patch rather than splitting this update across transactions.
    new_email: str | None = None
    if data.name is not None:
        current_user.name = data.name
    if data.locale is not None:
        current_user.locale = data.locale
    if data.email is not None:
        candidate = normalize_email(data.email)
        if candidate != current_user.email:
            # Case-insensitive, matching signup — otherwise "FOO@x.com" walks past a check that
            # "foo@x.com" would fail and two accounts end up owning the same verified address.
            clash = await db.scalar(
                select(User).where(func.lower(User.email) == candidate, User.id != current_user.id)
            )
            if clash:
                raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
            new_email = candidate
    if data.theme is not None:
        current_user.theme = data.theme
    if data.nickname is not None:
        current_user.nickname = data.nickname
    if data.age is not None:
        current_user.age = data.age
    if data.gender is not None:
        current_user.gender = data.gender
    if data.country is not None:
        current_user.country = data.country
    if data.city is not None:
        current_user.city = data.city
    if data.favorite_sports is not None:
        current_user.favorite_sports = [s.value for s in data.favorite_sports]
    if data.speed_rating is not None:
        current_user.speed_rating = data.speed_rating
    if data.strength_rating is not None:
        current_user.strength_rating = data.strength_rating
    if data.stamina_rating is not None:
        current_user.stamina_rating = data.stamina_rating
    if data.agility_rating is not None:
        current_user.agility_rating = data.agility_rating
    if data.latitude is not None:
        current_user.latitude = data.latitude
    if data.longitude is not None:
        current_user.longitude = data.longitude
    if data.radius_km is not None:
        current_user.radius_km = data.radius_km
    await db.commit()

    if new_email is not None:
        await email_verification_service.reset_for_new_email(
            db, current_user, new_email, email_service
        )
    await db.refresh(current_user)
    return current_user


@router.post("/me/onboarding/complete", response_model=UserRead)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Mark the wizard done.

    Deliberately permissive: it does not re-validate that every onboarding field is filled in.
    The wizard's own "Finish" step enforces the required fields (nickname, age, city, at least one
    favorite sport) before ever calling this; the athletic ratings are opt-in and can stay unset.
    This just flips the flag the client uses to stop redirecting here.
    """
    current_user.onboarding_completed = True
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, min_length=2, description="Case-insensitive name search"),
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    """Directory listing, also the search a team captain uses to find someone to invite by name."""
    stmt = select(User)
    if q is not None:
        stmt = stmt.where(User.name.ilike(f"%{q}%"))
    result = await db.scalars(stmt.limit(limit).offset(offset))
    return list(result)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user
