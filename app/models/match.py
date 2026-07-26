import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import MatchStatus, Sport, str_enum


class Match(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "matches"

    opponent_search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opponent_searches.id")
    )
    team_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    team_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    sport: Mapped[Sport] = mapped_column(str_enum(Sport, length=32))
    game_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("game_types.id"))
    city: Mapped[str] = mapped_column(String(120))
    pitch: Mapped[str] = mapped_column(String(255))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[MatchStatus] = mapped_column(
        str_enum(MatchStatus, length=24), default=MatchStatus.CONFIRMED
    )


class MatchGuestParticipant(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "match_guest_participants"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    guest_application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guest_applications.id")
    )
