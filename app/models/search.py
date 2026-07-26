import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import (
    ApplicationDirection,
    ApplicationStatus,
    ListingStatus,
    Sport,
    str_enum,
)


class RosterSearch(UUIDPKMixin, TimestampMixin, Base):
    """Permanent recruiting. Stays open across multiple hires; captain closes it manually."""

    __tablename__ = "roster_searches"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    # City/country chosen from the client's fixed country→city list (not free text), so recruiting
    # listings stay queryable and can be plotted on the discovery map.
    city: Mapped[str] = mapped_column(String(120), index=True)
    country: Mapped[str | None] = mapped_column(String(60), index=True, default=None)
    status: Mapped[ListingStatus] = mapped_column(
        str_enum(ListingStatus, length=16), default=ListingStatus.OPEN
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RosterApplication(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "roster_applications"

    # nullable for a direct captain invite that bypasses a public listing
    roster_search_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roster_searches.id"), default=None, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    direction: Mapped[ApplicationDirection] = mapped_column(str_enum(ApplicationDirection, length=24))
    status: Mapped[ApplicationStatus] = mapped_column(
        str_enum(ApplicationStatus, length=16), default=ApplicationStatus.PENDING
    )


class OpponentSearch(UUIDPKMixin, TimestampMixin, Base):
    """Flow 2. Requires team.completed. Concrete date+pitch; charged to publishing captain's credits."""

    __tablename__ = "opponent_searches"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    sport: Mapped[Sport] = mapped_column(str_enum(Sport, length=32))
    game_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("game_types.id"))
    city: Mapped[str] = mapped_column(String(120), index=True)
    pitch: Mapped[str] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[ListingStatus] = mapped_column(
        str_enum(ListingStatus, length=16), default=ListingStatus.OPEN
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OpponentApplication(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "opponent_applications"

    opponent_search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opponent_searches.id"), index=True
    )
    responding_team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        str_enum(ApplicationStatus, length=16), default=ApplicationStatus.PENDING
    )


class GuestSearch(UUIDPKMixin, TimestampMixin, Base):
    """Flow 1, one-off substitute. Always attached to a confirmed Match. Free to publish."""

    __tablename__ = "guest_searches"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[ListingStatus] = mapped_column(
        str_enum(ListingStatus, length=16), default=ListingStatus.OPEN
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GuestApplication(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "guest_applications"

    # nullable for a direct request not tied to a public listing
    guest_search_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guest_searches.id"), default=None, index=True
    )
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    direction: Mapped[ApplicationDirection] = mapped_column(str_enum(ApplicationDirection, length=24))
    status: Mapped[ApplicationStatus] = mapped_column(
        str_enum(ApplicationStatus, length=16), default=ApplicationStatus.PENDING
    )


class PlayerAvailability(UUIDPKMixin, TimestampMixin, Base):
    """Flow 1 broadcast by an individual. Free to publish."""

    __tablename__ = "player_availabilities"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    sport: Mapped[Sport] = mapped_column(str_enum(Sport, length=32))
    # City chosen from the client's fixed country→city list, so values stay queryable/consistent.
    city: Mapped[str] = mapped_column(String(120), index=True)
    # Country the city belongs to (also from the fixed list); scopes and labels the city.
    country: Mapped[str | None] = mapped_column(String(60), index=True, default=None)
    # Broader area than city, e.g. "Casablanca-Settat" — player-chosen, not derived.
    region: Mapped[str | None] = mapped_column(String(120), index=True, default=None)
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    # Player-chosen privacy radius: how far from their shared location a searcher's point may be
    # for this listing to surface in results.
    radius_km: Mapped[float | None] = mapped_column(Float, default=None)
    status: Mapped[ListingStatus] = mapped_column(
        str_enum(ListingStatus, length=16), default=ListingStatus.OPEN
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
