"""GuestSearch + GuestApplication domain logic (Flow 1, one-off substitute).

Per ../ANTIPAS/SPEC.md and DATA_MODEL.md:
- a team already holding a *confirmed* Match but short a player publishes a GuestSearch (free);
- a player applies, or the team invites a player directly (e.g. found via PlayerAvailability);
- the counterparty accepts/declines, the initiator withdraws;
- confirming creates a MatchGuestParticipant (NOT a TeamMembership — one-off), and if the application
  came through a GuestSearch that search closes and its other pending applications are auto-declined
  (one guest per search, unlike RosterSearch).
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
    MatchStatus,
    Sport,
)
from app.models.match import Match, MatchGuestParticipant
from app.models.search import GuestApplication, GuestSearch
from app.models.user import User
from app.services import team_service


async def _get_confirmed_match(db: AsyncSession, match_id: uuid.UUID) -> Match:
    match = await db.get(Match, match_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    if match.status != MatchStatus.CONFIRMED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Match is not confirmed")
    return match


def _require_team_in_match(match: Match, team_id: uuid.UUID) -> None:
    if team_id not in (match.team_a_id, match.team_b_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Team is not part of this match")


async def _reject_if_involved(db: AsyncSession, match: Match, user_id: uuid.UUID) -> None:
    """A player already rostered in the match (either team) or already a guest cannot guest again."""
    for team_id in (match.team_a_id, match.team_b_id):
        if await team_service.get_active_membership(db, team_id, user_id) is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "User already plays in this match")
    existing = await db.scalar(
        select(MatchGuestParticipant).where(
            MatchGuestParticipant.match_id == match.id,
            MatchGuestParticipant.user_id == user_id,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is already a guest of this match")


# --- GuestSearch --------------------------------------------------------------


async def get_search_or_404(db: AsyncSession, search_id: uuid.UUID) -> GuestSearch:
    search = await db.get(GuestSearch, search_id)
    if search is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest search not found")
    return search


async def publish_guest_search(
    db: AsyncSession, match_id: uuid.UUID, actor: User, team_id: uuid.UUID
) -> GuestSearch:
    match = await _get_confirmed_match(db, match_id)
    _require_team_in_match(match, team_id)
    await team_service.require_role(db, team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    search = GuestSearch(
        match_id=match.id,
        team_id=team_id,
        city=match.city,
        status=ListingStatus.OPEN,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.listing_expiry_hours),
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)
    return search


async def list_guest_searches(
    db: AsyncSession, city: str | None, sport: Sport | None, limit: int, offset: int
) -> list[GuestSearch]:
    stmt = select(GuestSearch).where(GuestSearch.status == ListingStatus.OPEN)
    if city is not None:
        stmt = stmt.where(GuestSearch.city == city)
    if sport is not None:
        stmt = stmt.join(Match, Match.id == GuestSearch.match_id).where(Match.sport == sport)
    result = await db.scalars(stmt.limit(limit).offset(offset))
    return list(result)


async def withdraw_guest_search(db: AsyncSession, search: GuestSearch, actor: User) -> None:
    await team_service.require_role(db, search.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    if search.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Search is not open")
    search.status = ListingStatus.WITHDRAWN
    await db.commit()


# --- GuestApplication ---------------------------------------------------------


async def get_application_or_404(db: AsyncSession, application_id: uuid.UUID) -> GuestApplication:
    application = await db.get(GuestApplication, application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return application


async def _reject_duplicate_pending(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID, direction: ApplicationDirection
) -> None:
    existing = await db.scalar(
        select(GuestApplication).where(
            GuestApplication.match_id == match_id,
            GuestApplication.user_id == user_id,
            GuestApplication.direction == direction,
            GuestApplication.status == ApplicationStatus.PENDING,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A pending application already exists")


async def apply_to_search(db: AsyncSession, search: GuestSearch, applicant: User) -> GuestApplication:
    if search.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Search is not open")
    match = await _get_confirmed_match(db, search.match_id)
    await _reject_if_involved(db, match, applicant.id)
    await _reject_duplicate_pending(db, match.id, applicant.id, ApplicationDirection.PLAYER_APPLIED)
    application = GuestApplication(
        guest_search_id=search.id,
        match_id=match.id,
        team_id=search.team_id,
        user_id=applicant.id,
        direction=ApplicationDirection.PLAYER_APPLIED,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def invite_guest(
    db: AsyncSession, match_id: uuid.UUID, actor: User, team_id: uuid.UUID, user_id: uuid.UUID
) -> GuestApplication:
    match = await _get_confirmed_match(db, match_id)
    _require_team_in_match(match, team_id)
    await team_service.require_role(db, team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    if await db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await _reject_if_involved(db, match, user_id)
    await _reject_duplicate_pending(db, match.id, user_id, ApplicationDirection.TEAM_INVITED)
    application = GuestApplication(
        guest_search_id=None,
        match_id=match.id,
        team_id=team_id,
        user_id=user_id,
        direction=ApplicationDirection.TEAM_INVITED,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


def _is_team_manager_action(direction: ApplicationDirection) -> bool:
    """player_applied is approved by the team; team_invited is approved by the invited player."""
    return direction == ApplicationDirection.PLAYER_APPLIED


async def _authorize_counterparty(db: AsyncSession, application: GuestApplication, actor: User) -> None:
    if _is_team_manager_action(application.direction):
        await team_service.require_role(db, application.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    elif actor.id != application.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the invited player can respond")


async def _authorize_initiator(db: AsyncSession, application: GuestApplication, actor: User) -> None:
    if _is_team_manager_action(application.direction):
        if actor.id != application.user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the applicant can withdraw")
    else:
        await team_service.require_role(db, application.team_id, actor, team_service.CAPTAIN_OR_ADMIN)


def _require_pending(application: GuestApplication) -> None:
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Application is not pending")


async def accept_application(
    db: AsyncSession, application: GuestApplication, actor: User
) -> MatchGuestParticipant:
    _require_pending(application)
    await _authorize_counterparty(db, application, actor)

    # Guard against a race where the player joined/guested since the application was created.
    match = await _get_confirmed_match(db, application.match_id)
    await _reject_if_involved(db, match, application.user_id)

    participant = MatchGuestParticipant(
        match_id=application.match_id,
        team_id=application.team_id,
        user_id=application.user_id,
        guest_application_id=application.id,
    )
    db.add(participant)
    application.status = ApplicationStatus.CONFIRMED

    if application.guest_search_id is not None:
        search = await db.get(GuestSearch, application.guest_search_id)
        if search is not None:
            search.status = ListingStatus.CONFIRMED
        others = await db.scalars(
            select(GuestApplication).where(
                GuestApplication.guest_search_id == application.guest_search_id,
                GuestApplication.id != application.id,
                GuestApplication.status == ApplicationStatus.PENDING,
            )
        )
        for other in others:
            other.status = ApplicationStatus.DECLINED

    await db.commit()
    await db.refresh(participant)
    return participant


async def decline_application(db: AsyncSession, application: GuestApplication, actor: User) -> None:
    _require_pending(application)
    await _authorize_counterparty(db, application, actor)
    application.status = ApplicationStatus.DECLINED
    await db.commit()


async def withdraw_application(db: AsyncSession, application: GuestApplication, actor: User) -> None:
    _require_pending(application)
    await _authorize_initiator(db, application, actor)
    application.status = ApplicationStatus.WITHDRAWN
    await db.commit()


# --- listing ------------------------------------------------------------------


async def list_search_applications(
    db: AsyncSession, search: GuestSearch, actor: User
) -> list[GuestApplication]:
    await team_service.require_role(db, search.team_id, actor, team_service.CAPTAIN_OR_ADMIN)
    result = await db.scalars(select(GuestApplication).where(GuestApplication.guest_search_id == search.id))
    return list(result)


async def list_my_applications(db: AsyncSession, user: User) -> list[GuestApplication]:
    result = await db.scalars(select(GuestApplication).where(GuestApplication.user_id == user.id))
    return list(result)


async def list_match_guests(db: AsyncSession, match_id: uuid.UUID) -> list[MatchGuestParticipant]:
    result = await db.scalars(select(MatchGuestParticipant).where(MatchGuestParticipant.match_id == match_id))
    return list(result)
