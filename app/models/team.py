import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import MembershipStatus, Sport, TeamRole, str_enum

if TYPE_CHECKING:
    from app.models.user import User

# Matches app/models/user.py's DEFAULT_COUNTRY. Duplicated rather than imported — cross-model
# imports for a literal aren't worth the coupling.
DEFAULT_COUNTRY = "Morocco"


class Team(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    logo_url: Mapped[str | None] = mapped_column(String(512), default=None)
    country: Mapped[str] = mapped_column(String(60), default=DEFAULT_COUNTRY)
    city: Mapped[str | None] = mapped_column(String(120), default=None)
    sport: Mapped[Sport] = mapped_column(str_enum(Sport))
    # The lineup format (e.g. 7v7) the captain commits the roster to. Null until set at the
    # roster-building stage — never at creation. Gates `completed` (team_service.update_team
    # requires the active roster to reach `game_type.players_per_side`) and is inherited by any
    # OpponentSearch this team publishes, rather than being chosen again at that point.
    game_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("game_types.id"), default=None
    )
    completed: Mapped[bool] = mapped_column(default=False)
    is_adhoc: Mapped[bool] = mapped_column(default=False)

    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="team")


class TeamMembership(UUIDPKMixin, Base):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_membership_team_user"),)

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    role: Mapped[TeamRole] = mapped_column(str_enum(TeamRole, length=16))
    status: Mapped[MembershipStatus] = mapped_column(
        str_enum(MembershipStatus, length=16), default=MembershipStatus.ACTIVE
    )
    # Captain/admin-assigned, shown on the lineup card. Not unique per team — two players briefly
    # sharing a number while the captain reassigns one is a UX nuisance, not a data-integrity issue.
    jersey_number: Mapped[int | None] = mapped_column(Integer, default=None)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped["Team"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
