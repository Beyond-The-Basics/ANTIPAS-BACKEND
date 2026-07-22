"""Seed reference data required for the app to be usable.

Idempotent: safe to run repeatedly. Run with `python -m app.db.seed` (or `make seed`).

Currently seeds the GameType catalog confirmed in ../ANTIPAS/DATA_MODEL.md:
soccer -> 5v5, 7v7, 11v11; tennis -> singles, doubles; paddle -> doubles.
"""

import asyncio

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.enums import Sport
from app.models.game_type import GameType

GAME_TYPE_CATALOG: dict[Sport, list[str]] = {
    Sport.SOCCER: ["5v5", "7v7", "11v11"],
    Sport.TENNIS: ["singles", "doubles"],
    Sport.PADDLE: ["doubles"],
}


async def seed_game_types() -> int:
    """Insert any missing (sport, label) game types. Returns the number added."""
    added = 0
    async with async_session_factory() as session:
        for sport, labels in GAME_TYPE_CATALOG.items():
            for label in labels:
                exists = await session.scalar(
                    select(GameType).where(GameType.sport == sport, GameType.label == label)
                )
                if exists is None:
                    session.add(GameType(sport=sport, label=label))
                    added += 1
        await session.commit()
    return added


async def main() -> None:
    added = await seed_game_types()
    print(f"Seed complete. Game types added: {added}")


if __name__ == "__main__":
    asyncio.run(main())
