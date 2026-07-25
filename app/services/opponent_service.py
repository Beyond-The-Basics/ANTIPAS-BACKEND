"""OpponentSearch + OpponentApplication domain logic (Flow 2, team vs team).

Per ../ANTIPAS/SPEC.md and DATA_MODEL.md:
- publishing requires the team to be `completed` (sequential gate); terms (game type, city, pitch,
  date) are fixed at publish because negotiation is accept/reject only;
- a different, completed, same-sport team applies; parallel applications are allowed;
- the publisher confirms one application -> creates a Match, auto-declines the rest, and closes the
  search (one match per search).
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ApplicationStatus, ListingStatus, MatchStatus, SearchType, Sport
from app.models.match import Match
from app.models.search import OpponentApplication, OpponentSearch
from app.models.team import Team
from app.models.user import User
from app.schemas.opponent import OpponentSearchCreate
from app.services import credit_service, team_service

# --- OpponentSearch -----------------------------------------------------------


async def get_search_or_404(db: AsyncSession, search_id: uuid.UUID) -> OpponentSearch:
    search = await db.get(OpponentSearch, search_id)
    if search is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opponent search not found")
    return search


async def publish_opponent_search(
    db: AsyncSession, team: Team, actor: User, data: OpponentSearchCreate
) -> OpponentSearch:
    await team_service.require_role(db, team.id, actor, team_service.CAPTAIN_OR_ADMIN)
    if not team.completed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Team must be marked completed before searching for an opponent",
        )
    # A completed team always has a game_type_id — team_service.update_team enforces that on the
    # transition into completed — so the search just inherits it instead of asking again. This
    # check only guards against a team that reached completed=True before this rule existed.
    if team.game_type_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Team has no lineup type set")

    search = OpponentSearch(
        team_id=team.id,
        sport=team.sport,
        game_type_id=team.game_type_id,
        city=data.city,
        pitch=data.pitch,
        date=data.date,
        status=ListingStatus.OPEN,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.listing_expiry_hours),
    )
    db.add(search)
    await db.flush()
    await credit_service.charge_publish(db, actor, SearchType.OPPONENT_SEARCH, search.id)
    await db.commit()
    await db.refresh(search)
    return search


async def list_opponent_searches(
    db: AsyncSession, city: str | None, sport: Sport | None, limit: int, offset: int
) -> list[OpponentSearch]:
    stmt = select(OpponentSearch).where(OpponentSearch.status == ListingStatus.OPEN)
    if city is not None:
        stmt = stmt.where(OpponentSearch.city == city)
    if sport is not None:
        stmt = stmt.where(OpponentSearch.sport == sport)
    result = await db.scalars(stmt.limit(limit).offset(offset))
    return list(result)


async def withdraw_opponent_search(db: AsyncSession, search: OpponentSearch, actor: User) -> None:
    await team_service.require_role(db, search.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    if search.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Search is not open")
    search.status = ListingStatus.WITHDRAWN
    await db.commit()


# --- OpponentApplication ------------------------------------------------------


async def get_application_or_404(db: AsyncSession, application_id: uuid.UUID) -> OpponentApplication:
    application = await db.get(OpponentApplication, application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return application


async def apply_to_search(
    db: AsyncSession, search: OpponentSearch, actor: User, responding_team_id: uuid.UUID
) -> OpponentApplication:
    if search.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Search is not open")
    responding_team = await team_service.get_team_or_404(db, responding_team_id)
    await team_service.require_role(db, responding_team.id, actor, team_service.CAPTAIN_OR_ADMIN)
    if responding_team.id == search.team_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot respond to your own search")
    if not responding_team.completed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Responding team must be completed")
    if responding_team.sport != search.sport:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sport does not match the search")

    existing = await db.scalar(
        select(OpponentApplication).where(
            OpponentApplication.opponent_search_id == search.id,
            OpponentApplication.responding_team_id == responding_team.id,
            OpponentApplication.status == ApplicationStatus.PENDING,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A pending application already exists")

    application = OpponentApplication(
        opponent_search_id=search.id,
        responding_team_id=responding_team.id,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def withdraw_application(db: AsyncSession, application: OpponentApplication, actor: User) -> None:
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Application is not pending")
    await team_service.require_role(db, application.responding_team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    application.status = ApplicationStatus.WITHDRAWN
    await db.commit()


async def confirm_application(db: AsyncSession, application: OpponentApplication, actor: User) -> Match:
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Application is not pending")
    search = await get_search_or_404(db, application.opponent_search_id)
    if search.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Search is no longer open")
    # only the publishing team's captain/admin confirms
    await team_service.require_role(db, search.team_id, actor, team_service.CAPTAIN_OR_ADMIN)

    match = Match(
        opponent_search_id=search.id,
        team_a_id=search.team_id,
        team_b_id=application.responding_team_id,
        sport=search.sport,
        game_type_id=search.game_type_id,
        city=search.city,
        pitch=search.pitch,
        date=search.date,
        status=MatchStatus.CONFIRMED,
    )
    db.add(match)
    application.status = ApplicationStatus.CONFIRMED
    search.status = ListingStatus.CONFIRMED

    others = await db.scalars(
        select(OpponentApplication).where(
            OpponentApplication.opponent_search_id == search.id,
            OpponentApplication.id != application.id,
            OpponentApplication.status == ApplicationStatus.PENDING,
        )
    )
    for other in others:
        other.status = ApplicationStatus.DECLINED

    await db.commit()
    await db.refresh(match)
    return match


async def list_search_applications(
    db: AsyncSession, search: OpponentSearch, actor: User
) -> list[OpponentApplication]:
    await team_service.require_role(db, search.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    result = await db.scalars(
        select(OpponentApplication).where(OpponentApplication.opponent_search_id == search.id)
    )
    return list(result)


async def list_team_applications(db: AsyncSession, team: Team, actor: User) -> list[OpponentApplication]:
    await team_service.require_role(db, team.id, actor, team_service.CAPTAIN_OR_ADMIN)
    result = await db.scalars(
        select(OpponentApplication).where(OpponentApplication.responding_team_id == team.id)
    )
    return list(result)
