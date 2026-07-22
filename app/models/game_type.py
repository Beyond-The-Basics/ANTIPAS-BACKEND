from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, UUIDPKMixin
from app.models.enums import Sport


class GameType(UUIDPKMixin, Base):
    """Reference data, e.g. soccer/5v5, tennis/doubles. Chosen per search, not fixed to a team."""

    __tablename__ = "game_types"
    __table_args__ = (UniqueConstraint("sport", "label", name="uq_game_type_sport_label"),)

    sport: Mapped[Sport] = mapped_column(Enum(Sport, native_enum=False, length=32))
    label: Mapped[str] = mapped_column(String(32))
