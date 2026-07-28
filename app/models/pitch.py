import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin


class Pitch(UUIDPKMixin, TimestampMixin, Base):
    """A venue a team has registered, for picking in a match negotiation rather than typing a
    pitch name freehand every time. Always owned by the team that added it — `is_neutral` is what
    the owning captain sets to also offer it to whichever team they end up negotiating with, not a
    statement about the venue's physical location. The negotiation's "your city"/"their city"/
    "neutral for both" labels are computed from `team_id` + `is_neutral` relative to the two
    negotiating teams, not stored here."""

    __tablename__ = "pitches"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(120))
    price_per_hour: Mapped[float | None] = mapped_column(Float, default=None)
    is_neutral: Mapped[bool] = mapped_column(default=False)
