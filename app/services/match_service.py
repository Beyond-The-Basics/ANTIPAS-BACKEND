"""Match lifecycle: read, cancel, mark played.

Post-confirmation cancellation is allowed for either side (the reputation/rating strike that SPEC
attaches to it belongs to the feedback milestone, not here).
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MatchStatus
from app.models.match import Match
from app.models.user import User
from app.services import team_service


async def get_match_or_404(db: AsyncSession, match_id: uuid.UUID) -> Match:
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    return match


async def list_team_matches(db: AsyncSession, team_id: uuid.UUID) -> list[Match]:
    result = await db.scalars(
        select(Match).where(or_(Match.team_a_id == team_id, Match.team_b_id == team_id))
    )
    return list(result)


async def _manager_side(db: AsyncSession, match: Match, actor: User) -> str | None:
    """Return 'a'/'b' if actor is captain/admin of team_a/team_b, else None."""
    a = await team_service.get_active_membership(db, match.team_a_id, actor.id)
    if a is not None and a.role in team_service.CAPTAIN_OR_ADMIN:
        return "a"
    b = await team_service.get_active_membership(db, match.team_b_id, actor.id)
    if b is not None and b.role in team_service.CAPTAIN_OR_ADMIN:
        return "b"
    return None


async def cancel_match(db: AsyncSession, match: Match, actor: User) -> Match:
    if match.status != MatchStatus.CONFIRMED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a confirmed match can be cancelled")
    side = await _manager_side(db, match, actor)
    if side is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a manager of either team")
    match.status = MatchStatus.CANCELLED_BY_A if side == "a" else MatchStatus.CANCELLED_BY_B
    await db.commit()
    await db.refresh(match)
    return match


async def mark_played(db: AsyncSession, match: Match, actor: User) -> Match:
    if match.status != MatchStatus.CONFIRMED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a confirmed match can be marked played")
    if await _manager_side(db, match, actor) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a manager of either team")
    match.status = MatchStatus.PLAYED
    await db.commit()
    await db.refresh(match)
    return match
