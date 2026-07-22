import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import MembershipStatus, Sport, TeamRole

if TYPE_CHECKING:
    from app.models.user import User


class Team(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(120))
    logo_url: Mapped[str | None] = mapped_column(String(512), default=None)
    sport: Mapped[Sport] = mapped_column(Enum(Sport, native_enum=False, length=32))
    completed: Mapped[bool] = mapped_column(default=False)
    is_adhoc: Mapped[bool] = mapped_column(default=False)

    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="team")


class TeamMembership(UUIDPKMixin, Base):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_membership_team_user"),)

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    role: Mapped[TeamRole] = mapped_column(Enum(TeamRole, native_enum=False, length=16))
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus, native_enum=False, length=16), default=MembershipStatus.ACTIVE
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped["Team"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
