from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin

# Matches app/models/team.py's DEFAULT_COUNTRY. Duplicated rather than imported — cross-model
# imports for a constant couple the modules for no gain.
DEFAULT_COUNTRY = "Morocco"


class Pitch(UUIDPKMixin, TimestampMixin, Base):
    """A football venue in a city, selectable by any team.

    Pitches belong to nobody: a team picks its country and city, then a venue from what's there.
    Most rows come from the seeded city directory (`app/db/pitch_catalog.py`); a captain can also
    add one that isn't listed, and it joins the same shared directory.

    `(name, country, city)` is the identity, which is why it's unique — it's what makes re-running
    the seeder a no-op and what stops a hand-added venue from duplicating a seeded one.
    """

    __tablename__ = "pitches"
    __table_args__ = (UniqueConstraint("name", "country", "city", name="uq_pitches_name_country_city"),)

    # Directory names run long: "Terrain de foot de proximite Sidi Othmane (Av. Mohamed Bouziane)"
    # is 64 characters.
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(60), index=True, default=DEFAULT_COUNTRY)
    city: Mapped[str] = mapped_column(String(120), index=True)
