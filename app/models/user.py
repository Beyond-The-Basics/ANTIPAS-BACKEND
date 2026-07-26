from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.team import TeamMembership

DEFAULT_COUNTRY = "Morocco"


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    phone_verified: Mapped[bool] = mapped_column(default=False)
    # Login identifier. Nullable at the DB level because dev-created users (`POST /users`) and any
    # pre-auth row have none; `POST /auth/signup` requires it, so every account that can actually
    # log in has one. The unique index tolerates multiple NULLs, which is the behaviour we want.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, default=None)
    email_verified: Mapped[bool] = mapped_column(default=False)
    # bcrypt digest. Null means "no password set" — such a user cannot log in (see
    # app/core/security.py `verify_password`).
    password_hash: Mapped[str | None] = mapped_column(String(128), default=None)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, default=None)

    # --- onboarding profile ----------------------------------------------------
    # Filled in by the post-signup step wizard (`POST /users/me/onboarding/complete`), not at
    # signup itself — signup only collects the auth credential. All nullable/defaulted so a
    # freshly created account (via signup or the dev `POST /users`) is still a valid row.
    nickname: Mapped[str | None] = mapped_column(String(60), default=None)
    age: Mapped[int | None] = mapped_column(Integer, default=None)
    country: Mapped[str] = mapped_column(String(60), default=DEFAULT_COUNTRY)
    city: Mapped[str | None] = mapped_column(String(120), default=None)
    # Sport values (str_enum stores the value, e.g. "soccer"); plain ARRAY(String) here rather
    # than str_enum() since this column holds zero-or-more values, not one.
    favorite_sports: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list)
    # Self-rated 1-5, all optional — a player may not want to rate every trait.
    speed_rating: Mapped[int | None] = mapped_column(Integer, default=None)
    strength_rating: Mapped[int | None] = mapped_column(Integer, default=None)
    stamina_rating: Mapped[int | None] = mapped_column(Integer, default=None)
    agility_rating: Mapped[int | None] = mapped_column(Integer, default=None)
    # Set once by the completion endpoint; gates the client's post-login redirect to the wizard.
    onboarding_completed: Mapped[bool] = mapped_column(default=False)

    # Saved discoverability location — set the first time a player publishes a PlayerAvailability
    # (or edited directly on the profile) and reused as the default on future broadcasts.
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    radius_km: Mapped[float | None] = mapped_column(Float, default=None)

    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="user")
