import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import Sport
from app.models.user import User
from app.schemas.match import MatchRead
from app.schemas.opponent import (
    OpponentApplicationCreate,
    OpponentApplicationRead,
    OpponentSearchCreate,
    OpponentSearchRead,
)
from app.services import opponent_service, team_service

router = APIRouter(tags=["opponent"])

# --- OpponentSearch -----------------------------------------------------------


@router.post(
    "/teams/{team_id}/opponent-searches",
    response_model=OpponentSearchRead,
    status_code=status.HTTP_201_CREATED,
)
async def publish_opponent_search(
    team_id: uuid.UUID,
    data: OpponentSearchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await opponent_service.publish_opponent_search(db, team, current_user, data)


@router.get("/opponent-searches", response_model=list[OpponentSearchRead])
async def browse_opponent_searches(
    city: str | None = None,
    sport: Sport | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await opponent_service.list_opponent_searches(db, city, sport, limit, offset)


@router.get("/opponent-searches/{search_id}", response_model=OpponentSearchRead)
async def get_opponent_search(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await opponent_service.get_search_or_404(db, search_id)


@router.post("/opponent-searches/{search_id}/withdraw", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_opponent_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await opponent_service.get_search_or_404(db, search_id)
    await opponent_service.withdraw_opponent_search(db, search, current_user)


# --- OpponentApplication ------------------------------------------------------


@router.post(
    "/opponent-searches/{search_id}/applications",
    response_model=OpponentApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_search(
    search_id: uuid.UUID,
    data: OpponentApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await opponent_service.get_search_or_404(db, search_id)
    return await opponent_service.apply_to_search(db, search, current_user, data.responding_team_id)


@router.get(
    "/opponent-searches/{search_id}/applications",
    response_model=list[OpponentApplicationRead],
)
async def list_search_applications(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await opponent_service.get_search_or_404(db, search_id)
    return await opponent_service.list_search_applications(db, search, current_user)


@router.get(
    "/teams/{team_id}/opponent-applications",
    response_model=list[OpponentApplicationRead],
)
async def list_team_applications(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await opponent_service.list_team_applications(db, team, current_user)


@router.post("/opponent-applications/{application_id}/confirm", response_model=MatchRead)
async def confirm_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    return await opponent_service.confirm_application(db, application, current_user)


@router.post(
    "/opponent-applications/{application_id}/withdraw",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    await opponent_service.withdraw_application(db, application, current_user)
