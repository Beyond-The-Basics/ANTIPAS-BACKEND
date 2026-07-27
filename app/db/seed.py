"""Seed reference data required for the app to be usable.

Idempotent: safe to run repeatedly. Run with `python -m app.db.seed` (or `make seed`).

Currently seeds the GameType catalog confirmed in ../ANTIPAS/DATA_MODEL.md:
soccer -> 5v5, 6v6, 7v7, 11v11; tennis -> singles, doubles; paddle -> doubles;
basketball -> 3x3, 5v5.
"""

import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.enums import Sport
from app.models.game_type import GameType

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


async def main() -> None:
    added = await seed_game_types()
    print(f"Seed complete. Game types added: {added}")


if __name__ == "__main__":
    asyncio.run(main())
