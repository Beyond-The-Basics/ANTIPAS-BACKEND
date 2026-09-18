"""Pitch domain logic — the shared venue directory a team picks from when negotiating a match,
instead of typing a pitch name freehand every time. Venues belong to nobody: see
`app/models/pitch.py` for why `(name, country, city)` is the identity."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pitch import Pitch
from app.schemas.pitch import PitchCreate


async def get_or_create_pitch(db: AsyncSession, data: PitchCreate) -> tuple[Pitch, bool]:
    """Return the venue with this name in this city, adding it if it isn't there yet, and whether
    it had to be added.

    Creation is idempotent rather than a 409 because two captains adding "Stade Municipal" on the
    same evening are describing one venue, not colliding. The match is case-insensitive so a
    hand-typed "stade municipal" lands on the seeded row instead of shadowing it, which is also
    what makes `seed_pitches` a no-op on re-run. The flag is what lets callers tell the two apart —
    the endpoint answers 200 vs 201 with it, the seeder counts with it.
    """
    name = data.name.strip()
    existing = await db.scalar(
        select(Pitch).where(
            func.lower(Pitch.name) == name.lower(),
            Pitch.country == data.country,
            Pitch.city == data.city,
        )
    )
    if existing is not None:
        return existing, False

    pitch = Pitch(name=name, country=data.country, city=data.city)
    db.add(pitch)
    await db.commit()
    await db.refresh(pitch)
    return pitch, True


async def list_pitches(db: AsyncSession, country: str, city: str | None = None) -> list[Pitch]:
    """The directory for a country, narrowed to one city when given. Ordered by name: with no
    coordinates stored there is no distance to sort by, and alphabetical is what a select needs."""
    query = select(Pitch).where(Pitch.country == country)
    if city:
        query = query.where(Pitch.city == city)
    result = await db.scalars(query.order_by(Pitch.name))
    return list(result)
