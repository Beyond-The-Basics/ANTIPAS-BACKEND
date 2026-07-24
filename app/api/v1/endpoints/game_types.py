"""Read-only reference data. No auth — same visibility as the sport/team directory."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import Sport
from app.models.game_type import GameType
from app.schemas.game_type import GameTypeRead

router = APIRouter()


@router.get("", response_model=list[GameTypeRead])
async def list_game_types(
    sport: Sport | None = None, db: AsyncSession = Depends(get_db)
) -> list[GameType]:
    """The lineup catalog a captain picks from at the roster-building stage."""
    stmt = select(GameType)
    if sport is not None:
        stmt = stmt.where(GameType.sport == sport)
    result = await db.scalars(stmt.order_by(GameType.players_per_side))
    return list(result)
