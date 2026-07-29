import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Gender, Sport, Theme

MIN_AGE = 13
MAX_AGE = 100
MIN_RATING = 1
MAX_RATING = 5
MAX_FAVORITE_SPORTS = len(Sport)


class UserCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    theme: Theme | None = None

    # --- onboarding profile, all optional so this schema also serves incremental step-by-step
    # saves during the wizard (see POST /users/me/onboarding/complete for the completion flag) ---
    nickname: str | None = Field(default=None, min_length=1, max_length=60)
    age: int | None = Field(default=None, ge=MIN_AGE, le=MAX_AGE)
    gender: Gender | None = None
    country: str | None = Field(default=None, min_length=1, max_length=60)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    favorite_sports: list[Sport] | None = Field(default=None, max_length=MAX_FAVORITE_SPORTS)
    speed_rating: int | None = Field(default=None, ge=MIN_RATING, le=MAX_RATING)
    strength_rating: int | None = Field(default=None, ge=MIN_RATING, le=MAX_RATING)
    stamina_rating: int | None = Field(default=None, ge=MIN_RATING, le=MAX_RATING)
    agility_rating: int | None = Field(default=None, ge=MIN_RATING, le=MAX_RATING)

    # Saved discoverability location, editable independently of publishing an availability.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=200)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str
    phone_verified: bool
    email: str | None
    email_verified: bool
    theme: Theme
    created_at: datetime

    nickname: str | None
    age: int | None
    gender: Gender | None
    country: str
    city: str | None
    favorite_sports: list[Sport]
    speed_rating: int | None
    strength_rating: int | None
    stamina_rating: int | None
    agility_rating: int | None
    onboarding_completed: bool

    latitude: float | None
    longitude: float | None
    radius_km: float | None
