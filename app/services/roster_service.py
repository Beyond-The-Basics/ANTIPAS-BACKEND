"""RosterSearch + RosterApplication domain logic.

Permanent recruiting (RosterSearch) and the mutual-consent join flow (RosterApplication), per
../ANTIPAS/SPEC.md and DATA_MODEL.md:
- captain/admin publish/close a team's search, invite players, and act on player applications;
- the invited player accepts/declines invites; the initiator withdraws;
- confirming an application creates or reactivates a TeamMembership (never a duplicate (team,user)).
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import (
    ApplicationDirection,
    ApplicationStatus,
    ListingStatus,
    MembershipStatus,
    SearchType,
    Sport,
    TeamRole,
)
from app.models.search import RosterApplication, RosterSearch
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.services import credit_service, team_service

# --- RosterSearch -------------------------------------------------------------


async def get_search_or_404(db: AsyncSession, search_id: uuid.UUID) -> RosterSearch:
    search = await db.get(RosterSearch, search_id)
    if search is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roster search not found")
    return search


async def publish_roster_search(
    db: AsyncSession, team: Team, actor: User, city: str, country: str | None = None
) -> RosterSearch:
    await team_service.require_role(db, team.id, actor, team_service.CAPTAIN_OR_ADMIN)
    search = RosterSearch(
        team_id=team.id,
        city=city,
        # Default to the team's own country so the listing plots on the map even if the client
        # doesn't send one explicitly.
        country=country or team.country,
        status=ListingStatus.OPEN,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.listing_expiry_hours),
    )
    db.add(search)
    await db.flush()  # assign id before charging
    await credit_service.charge_publish(db, actor, SearchType.ROSTER_SEARCH, search.id)
    await db.commit()
    await db.refresh(search)
    return search


async def list_roster_searches(
    db: AsyncSession,
    city: str | None,
    sport: Sport | None,
    limit: int,
    offset: int,
) -> list[RosterSearch]:
    stmt = select(RosterSearch).where(RosterSearch.status == ListingStatus.OPEN)
    if city is not None:
        stmt = stmt.where(RosterSearch.city == city)
    if sport is not None:
        stmt = stmt.join(Team, Team.id == RosterSearch.team_id).where(Team.sport == sport)
    result = await db.scalars(stmt.limit(limit).offset(offset))
    return list(result)


async def close_roster_search(db: AsyncSession, search: RosterSearch, actor: User) -> None:
    await team_service.require_role(db, search.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    if search.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Search is not open")
    search.status = ListingStatus.CLOSED
    await db.commit()


# --- RosterApplication --------------------------------------------------------


async def get_application_or_404(db: AsyncSession, application_id: uuid.UUID) -> RosterApplication:
    application = await db.get(RosterApplication, application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return application


async def _reject_if_active_member(db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if await team_service.get_active_membership(db, team_id, user_id) is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is already an active member")


async def _reject_duplicate_pending(
    db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID, direction: ApplicationDirection
) -> None:
    existing = await db.scalar(
        select(RosterApplication).where(
            RosterApplication.team_id == team_id,
            RosterApplication.user_id == user_id,
            RosterApplication.direction == direction,
            RosterApplication.status == ApplicationStatus.PENDING,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A pending application already exists")


async def apply_to_search(db: AsyncSession, search: RosterSearch, applicant: User) -> RosterApplication:
    if search.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Search is not open")
    await _reject_if_active_member(db, search.team_id, applicant.id)
    await _reject_duplicate_pending(db, search.team_id, applicant.id, ApplicationDirection.PLAYER_APPLIED)
    application = RosterApplication(
        roster_search_id=search.id,
        team_id=search.team_id,
        user_id=applicant.id,
        direction=ApplicationDirection.PLAYER_APPLIED,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def invite_player(db: AsyncSession, team: Team, actor: User, user_id: uuid.UUID) -> RosterApplication:
    await team_service.require_role(db, team.id, actor, team_service.CAPTAIN_OR_ADMIN)
    if await db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await _reject_if_active_member(db, team.id, user_id)
    await _reject_duplicate_pending(db, team.id, user_id, ApplicationDirection.TEAM_INVITED)
    application = RosterApplication(
        roster_search_id=None,
        team_id=team.id,
        user_id=user_id,
        direction=ApplicationDirection.TEAM_INVITED,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


def _is_team_manager_action(direction: ApplicationDirection) -> bool:
    """Whether the *team side* (captain/admin) is the party that approves/declines this direction."""
    return direction == ApplicationDirection.PLAYER_APPLIED


async def _authorize_counterparty(db: AsyncSession, application: RosterApplication, actor: User) -> None:
    """The party that must *respond* (accept/decline) is the counterparty to the initiator."""
    if _is_team_manager_action(application.direction):
        await team_service.require_role(db, application.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    elif actor.id != application.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the invited player can respond")


async def _authorize_initiator(db: AsyncSession, application: RosterApplication, actor: User) -> None:
    """The party that *created* the application is the one who can withdraw it."""
    if _is_team_manager_action(application.direction):
        # player_applied was initiated by the player
        if actor.id != application.user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the applicant can withdraw")
    else:
        # team_invited was initiated by the team
        await team_service.require_role(db, application.team_id, actor, team_service.CAPTAIN_OR_ADMIN)


async def _add_or_reactivate_membership(db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
    membership = await db.scalar(
        select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user_id,
        )
    )
    if membership is None:
        db.add(
            TeamMembership(
                team_id=team_id,
                user_id=user_id,
                role=TeamRole.MEMBER,
                status=MembershipStatus.ACTIVE,
            )
        )
    elif membership.status != MembershipStatus.ACTIVE:
        membership.status = MembershipStatus.ACTIVE
        membership.role = TeamRole.MEMBER


def _require_pending(application: RosterApplication) -> None:
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Application is not pending")


async def accept_application(
    db: AsyncSession, application: RosterApplication, actor: User
) -> RosterApplication:
    _require_pending(application)
    await _authorize_counterparty(db, application, actor)
    application.status = ApplicationStatus.CONFIRMED
    await _add_or_reactivate_membership(db, application.team_id, application.user_id)
    await db.commit()
    await db.refresh(application)
    return application


async def decline_application(db: AsyncSession, application: RosterApplication, actor: User) -> None:
    _require_pending(application)
    await _authorize_counterparty(db, application, actor)
    application.status = ApplicationStatus.DECLINED
    await db.commit()


async def withdraw_application(db: AsyncSession, application: RosterApplication, actor: User) -> None:
    _require_pending(application)
    await _authorize_initiator(db, application, actor)
    application.status = ApplicationStatus.WITHDRAWN
    await db.commit()


# --- listing applications -----------------------------------------------------


async def list_search_applications(
    db: AsyncSession, search: RosterSearch, actor: User
) -> list[RosterApplication]:
    await team_service.require_role(db, search.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    result = await db.scalars(
        select(RosterApplication).where(RosterApplication.roster_search_id == search.id)
    )
    return list(result)


async def list_team_applications(db: AsyncSession, team: Team, actor: User) -> list[RosterApplication]:
    await team_service.require_role(db, team.id, actor, team_service.CAPTAIN_OR_ADMIN)
    result = await db.scalars(select(RosterApplication).where(RosterApplication.team_id == team.id))
    return list(result)


async def list_my_applications(db: AsyncSession, user: User) -> list[RosterApplication]:
    result = await db.scalars(select(RosterApplication).where(RosterApplication.user_id == user.id))
    return list(result)
