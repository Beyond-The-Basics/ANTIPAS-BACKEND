"""Seed reference data required for the app to be usable.

Idempotent: safe to run repeatedly. Run with `python -m app.db.seed` (or `make seed`).

Seeds two catalogs:
- GameType, confirmed in ../ANTIPAS/DATA_MODEL.md: soccer -> 5v5, 6v6, 7v7, 11v11;
  tennis -> singles, doubles; paddle -> doubles; basketball -> 3x3, 5v5.
- The Casablanca pitch directory (`app/db/pitch_catalog.py`), so teams have real venues to pick
  from instead of an empty select.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.pitch_catalog import CASABLANCA_PITCHES, CITY, COUNTRY
from app.db.session import async_session_factory
from app.models.enums import Sport
from app.models.game_type import GameType
from app.schemas.pitch import PitchCreate
from app.services import pitch_service

# label -> players_per_side. A team's active roster must reach this count before it can be
# marked completed under the lineup (see team_service.update_team).
GAME_TYPE_CATALOG: dict[Sport, list[tuple[str, int]]] = {
    Sport.SOCCER: [("5v5", 5), ("6v6", 6), ("7v7", 7), ("11v11", 11)],
    Sport.TENNIS: [("singles", 1), ("doubles", 2)],
    Sport.PADDLE: [("doubles", 2)],
    Sport.BASKETBALL: [("3x3", 3), ("5v5", 5)],
}


async def seed_game_types() -> int:
    """Insert any missing (sport, label) game types. Returns the number added.

    Only inserts — never updates an existing row's players_per_side, matching this function's
    "idempotent" contract. A catalog correction to an existing label needs its own migration.
    """
    added = 0
    async with async_session_factory() as session:
        for sport, entries in GAME_TYPE_CATALOG.items():
            for label, players_per_side in entries:
                exists = await session.scalar(
                    select(GameType).where(GameType.sport == sport, GameType.label == label)
                )
                if exists is None:
                    session.add(GameType(sport=sport, label=label, players_per_side=players_per_side))
                    added += 1
        await session.commit()
    return added


async def _add_missing_pitches(session: AsyncSession) -> int:
    added = 0
    for name in CASABLANCA_PITCHES:
        _, created = await pitch_service.get_or_create_pitch(
            session, PitchCreate(name=name, country=COUNTRY, city=CITY)
        )
        added += created
    return added


async def seed_pitches(session: AsyncSession | None = None) -> int:
    """Insert any missing venue from the city directory. Returns the number added.

    `get_or_create_pitch` is the same call the create endpoint makes, so a venue a captain already
    added by hand is adopted rather than duplicated — that shared path is what makes re-running
    this safe.

    Takes an optional session so tests can seed into their own database; left out, it opens one
    against `DATABASE_URL` as the CLI entry point needs.
    """
    if session is not None:
        return await _add_missing_pitches(session)
    async with async_session_factory() as owned:
        return await _add_missing_pitches(owned)


async def main() -> None:
    game_types = await seed_game_types()
    pitches = await seed_pitches()
    print(f"Seed complete. Game types added: {game_types}. Pitches added: {pitches}")


if __name__ == "__main__":
    asyncio.run(main())
