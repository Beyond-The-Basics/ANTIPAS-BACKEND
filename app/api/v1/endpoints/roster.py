import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_verified_user
from app.db.session import get_db
from app.models.enums import Sport
from app.models.user import User
from app.schemas.roster import (
    RosterApplicationRead,
    RosterInviteCreate,
    RosterSearchCreate,
    RosterSearchRead,
)
from app.services import roster_service, team_service

router = APIRouter(tags=["roster"])

# --- RosterSearch -------------------------------------------------------------


@router.post(
    "/teams/{team_id}/roster-searches",
    response_model=RosterSearchRead,
    status_code=status.HTTP_201_CREATED,
)
async def publish_roster_search(
    team_id: uuid.UUID,
    data: RosterSearchCreate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await roster_service.publish_roster_search(db, team, current_user, data.city, data.country)


@router.get("/roster-searches", response_model=list[RosterSearchRead])
async def browse_roster_searches(
    city: str | None = None,
    sport: Sport | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await roster_service.list_roster_searches(db, city, sport, limit, offset)


@router.get("/roster-searches/{search_id}", response_model=RosterSearchRead)
async def get_roster_search(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await roster_service.get_search_or_404(db, search_id)


@router.post("/roster-searches/{search_id}/close", status_code=status.HTTP_204_NO_CONTENT)
async def close_roster_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    search = await roster_service.get_search_or_404(db, search_id)
    await roster_service.close_roster_search(db, search, current_user)


# --- RosterApplication (both directions) --------------------------------------


@router.post(
    "/roster-searches/{search_id}/applications",
    response_model=RosterApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    search = await roster_service.get_search_or_404(db, search_id)
    return await roster_service.apply_to_search(db, search, current_user)


@router.get(
    "/roster-searches/{search_id}/applications",
    response_model=list[RosterApplicationRead],
)
async def list_search_applications(
    search_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    search = await roster_service.get_search_or_404(db, search_id)
    return await roster_service.list_search_applications(db, search, current_user)


@router.post(
    "/teams/{team_id}/roster-invitations",
    response_model=RosterApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
async def invite_player(
    team_id: uuid.UUID,
    data: RosterInviteCreate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await roster_service.invite_player(db, team, current_user, data.user_id)


@router.get(
    "/teams/{team_id}/roster-applications",
    response_model=list[RosterApplicationRead],
)
async def list_team_applications(
    team_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await roster_service.list_team_applications(db, team, current_user)


@router.get("/users/me/roster-applications", response_model=list[RosterApplicationRead])
async def list_my_applications(
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await roster_service.list_my_applications(db, current_user)


@router.post(
    "/roster-applications/{application_id}/accept",
    response_model=RosterApplicationRead,
)
async def accept_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    application = await roster_service.get_application_or_404(db, application_id)
    return await roster_service.accept_application(db, application, current_user)


@router.post(
    "/roster-applications/{application_id}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def decline_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    application = await roster_service.get_application_or_404(db, application_id)
    await roster_service.decline_application(db, application, current_user)


@router.post(
    "/roster-applications/{application_id}/withdraw",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    application = await roster_service.get_application_or_404(db, application_id)
    await roster_service.withdraw_application(db, application, current_user)
