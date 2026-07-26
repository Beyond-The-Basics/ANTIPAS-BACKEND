import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import Sport
from app.models.user import User
from app.schemas.membership import (
    JerseyNumberUpdate,
    LineupSet,
    MembershipRead,
    RoleUpdate,
    TransferCaptain,
)
from app.schemas.team import TeamCreate, TeamRead, TeamUpdate
from app.services import team_service

router = APIRouter()


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await team_service.create_team(db, data, current_user)


@router.get("", response_model=list[TeamRead])
async def list_teams(
    sport: Sport | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await team_service.list_teams(db, sport, limit, offset)


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(team_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await team_service.get_team_or_404(db, team_id)


@router.patch("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: uuid.UUID,
    data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await team_service.update_team(db, team, data, current_user)


@router.get("/{team_id}/members", response_model=list[MembershipRead])
async def list_members(team_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await team_service.get_team_or_404(db, team_id)
    return await team_service.list_active_members(db, team_id)


@router.post("/{team_id}/transfer-captain", status_code=status.HTTP_204_NO_CONTENT)
async def transfer_captain(
    team_id: uuid.UUID,
    data: TransferCaptain,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    await team_service.transfer_captain(db, team, current_user, data.new_captain_user_id)


@router.patch("/{team_id}/members/{user_id}/role", response_model=MembershipRead)
async def set_member_role(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await team_service.set_member_role(db, team, current_user, user_id, data.role)


@router.patch("/{team_id}/members/{user_id}/jersey-number", response_model=MembershipRead)
async def set_jersey_number(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    data: JerseyNumberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await team_service.set_jersey_number(db, team, current_user, user_id, data.jersey_number)


@router.put("/{team_id}/lineup", response_model=list[MembershipRead])
async def set_lineup(
    team_id: uuid.UUID,
    data: LineupSet,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await team_service.set_lineup(db, team, current_user, data.assignments)


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    await team_service.remove_member(db, team, current_user, user_id)


@router.post("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_team(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    await team_service.leave_team(db, team, current_user)
