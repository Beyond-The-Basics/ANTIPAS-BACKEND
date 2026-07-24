from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, UUIDPKMixin
from app.models.enums import Sport, str_enum


class GameType(UUIDPKMixin, Base):
    """Reference data, e.g. soccer/5v5, tennis/doubles.

    A team declares one at the roster-building stage (`Team.game_type_id`) — it both drives the
    minimum active-roster size required to mark the team completed and is inherited by any
    OpponentSearch that team publishes, rather than being chosen again at that point.
    """

    __tablename__ = "game_types"
    __table_args__ = (UniqueConstraint("sport", "label", name="uq_game_type_sport_label"),)

    sport: Mapped[Sport] = mapped_column(str_enum(Sport))
    label: Mapped[str] = mapped_column(String(32))
    # e.g. 5 for "5v5", 1 for tennis "singles". The minimum active TeamMembership count a team
    # needs before it can be marked completed under this lineup.
    players_per_side: Mapped[int] = mapped_column(Integer)
