import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
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
    country: Mapped[str | None] = mapped_column(String(60), index=True, default=None)
    pitch: Mapped[str] = mapped_column(String(255))
    # Full date+time kickoff (the initial proposal; the two captains can renegotiate it in chat).
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
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
    # Live negotiation terms once the challenge is ACCEPTED: the current proposed kickoff and pitch,
    # and which of the two teams made that proposal (the *other* team's captain agrees to finalize).
    proposed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    proposed_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    proposed_pitch: Mapped[str | None] = mapped_column(String(255), default=None)
    proposed_pitch_address: Mapped[str | None] = mapped_column(String(255), default=None)
    proposed_by_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), default=None
    )
    # Which of the two teams is responsible for booking/reserving the proposed pitch.
    proposed_booked_by_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), default=None
    )


class NegotiationMessage(UUIDPKMixin, TimestampMixin, Base):
    """A chat message in the post-acceptance negotiation between the two teams, keyed by the
    accepted OpponentApplication."""

    __tablename__ = "negotiation_messages"

    opponent_application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opponent_applications.id"), index=True
    )
    sender_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(2000))


class NegotiationProposal(UUIDPKMixin, TimestampMixin, Base):
    """An immutable snapshot of one negotiation offer (the initial terms seeded on accept, plus
    every subsequent counter). OpponentApplication.proposed_* only holds the *current* terms; this
    table is the append-only history behind the "Offer history" timeline."""

    __tablename__ = "negotiation_proposals"

    opponent_application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opponent_applications.id"), index=True
    )
    proposed_by_team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    pitch: Mapped[str] = mapped_column(String(255))
    pitch_address: Mapped[str | None] = mapped_column(String(255), default=None)
    booked_by_team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"))


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
