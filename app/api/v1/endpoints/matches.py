import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.match import MatchRead
from app.services import match_service, team_service

router = APIRouter(tags=["matches"])


@router.get("/matches/{match_id}", response_model=MatchRead)
async def get_match(match_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await match_service.get_match_or_404(db, match_id)


@router.get("/teams/{team_id}/matches", response_model=list[MatchRead])
async def list_team_matches(team_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await team_service.get_team_or_404(db, team_id)
    return await match_service.list_team_matches(db, team_id)


@router.post("/matches/{match_id}/cancel", response_model=MatchRead)
async def cancel_match(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    match = await match_service.get_match_or_404(db, match_id)
    return await match_service.cancel_match(db, match, current_user)


@router.post("/matches/{match_id}/played", response_model=MatchRead)
async def mark_match_played(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    match = await match_service.get_match_or_404(db, match_id)
    return await match_service.mark_played(db, match, current_user)
