"""Team & membership domain logic.

Enforces the settled rules from ../ANTIPAS/SPEC.md:
- creating a team makes the creator its captain;
- exactly one active captain per team;
- captain succession requires an explicit transfer (no leaderless teams) — a captain cannot leave
  or be removed without first handing over the role;
- a captain can delegate to admins, who share most permissions.

Note: adding *new* members happens through the mutual-consent RosterApplication flow (a later
milestone), not here. These operations act on already-existing memberships.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MembershipStatus, Sport, TeamRole
from app.models.game_type import GameType
from app.models.team import DEFAULT_COUNTRY, Team, TeamMembership
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate

CAPTAIN_ONLY = {TeamRole.CAPTAIN}
CAPTAIN_OR_ADMIN = {TeamRole.CAPTAIN, TeamRole.ADMIN}


async def get_team_or_404(db: AsyncSession, team_id: uuid.UUID) -> Team:
    team = await db.get(Team, team_id)
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team not found")
    return team


async def get_active_membership(
    db: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> TeamMembership | None:
    return await db.scalar(
        select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user_id,
            TeamMembership.status == MembershipStatus.ACTIVE,
        )
    )


async def require_role(
    db: AsyncSession, team_id: uuid.UUID, user: User, allowed: set[TeamRole]
) -> TeamMembership:
    membership = await get_active_membership(db, team_id, user.id)
    if membership is None or membership.role not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this team")
    return membership


async def list_active_members(db: AsyncSession, team_id: uuid.UUID) -> list[TeamMembership]:
    result = await db.scalars(
        select(TeamMembership).where(
            TeamMembership.team_id == team_id,
            TeamMembership.status == MembershipStatus.ACTIVE,
        )
    )
    return list(result)


async def list_teams(db: AsyncSession, sport: Sport | None, limit: int, offset: int) -> list[Team]:
    stmt = select(Team)
    if sport is not None:
        stmt = stmt.where(Team.sport == sport)
    result = await db.scalars(stmt.limit(limit).offset(offset))
    return list(result)


async def create_team(db: AsyncSession, data: TeamCreate, captain: User) -> Team:
    team = Team(
        name=data.name,
        sport=data.sport,
        description=data.description,
        logo_url=data.logo_url,
        # NULL would violate the NOT NULL column; resolve the default here rather than passing
        # None through, since a constructor kwarg of None sets the attribute instead of leaving
        # it unset (which is what would let the model's own column default apply).
        country=data.country or DEFAULT_COUNTRY,
        city=data.city,
        completed=False,
        is_adhoc=False,
    )
    db.add(team)
    await db.flush()  # assign team.id before creating the membership
    db.add(
        TeamMembership(
            team_id=team.id,
            user_id=captain.id,
            role=TeamRole.CAPTAIN,
            status=MembershipStatus.ACTIVE,
        )
    )
    await db.commit()
    await db.refresh(team)
    return team


async def update_team(db: AsyncSession, team: Team, data: TeamUpdate, actor: User) -> Team:
    membership = await require_role(db, team.id, actor, CAPTAIN_OR_ADMIN)

    # The lineup type and the completion state are the captain's calls (admins manage members but
    # don't set the format or decide the team is "ready"). Everything else is captain-or-admin.
    lineup_change = data.game_type_id is not None and data.game_type_id != team.game_type_id
    completed_change = data.completed is not None and data.completed != team.completed
    if (lineup_change or completed_change) and membership.role != TeamRole.CAPTAIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the captain can set the lineup type or mark the team complete",
        )

    if data.name is not None:
        team.name = data.name
    if data.description is not None:
        team.description = data.description
    if data.logo_url is not None:
        team.logo_url = data.logo_url
    if data.country is not None:
        team.country = data.country
    if data.city is not None:
        team.city = data.city

    if lineup_change:
        game_type = await db.get(GameType, data.game_type_id)
        if game_type is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Game type not found")
        if game_type.sport != team.sport:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Game type does not match the team's sport")
        team.game_type_id = data.game_type_id

    if data.completed is not None:
        team.completed = data.completed

    # A completed team still needs a lineup type (the format it's committing to and that any
    # OpponentSearch inherits) — but the captain may mark it complete before the roster is full,
    # so there is deliberately no minimum-member check here.
    if team.completed and (completed_change or lineup_change) and team.game_type_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Pick a lineup type before marking the team completed"
        )

    await db.commit()
    await db.refresh(team)
    return team


async def transfer_captain(
    db: AsyncSession, team: Team, current_captain: User, new_captain_user_id: uuid.UUID
) -> None:
    captain_membership = await require_role(db, team.id, current_captain, CAPTAIN_ONLY)
    if new_captain_user_id == current_captain.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You are already the captain")
    new_membership = await get_active_membership(db, team.id, new_captain_user_id)
    if new_membership is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Target is not an active member of this team")
    captain_membership.role = TeamRole.MEMBER
    new_membership.role = TeamRole.CAPTAIN
    await db.commit()


async def set_member_role(
    db: AsyncSession, team: Team, actor: User, target_user_id: uuid.UUID, role: TeamRole
) -> TeamMembership:
    # Only the captain designates/removes admins.
    await require_role(db, team.id, actor, CAPTAIN_ONLY)
    if target_user_id == actor.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Transfer captaincy instead of changing your own role"
        )
    target = await get_active_membership(db, team.id, target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if target.role == TeamRole.CAPTAIN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change the captain's role directly")
    target.role = role
    await db.commit()
    await db.refresh(target)
    return target


async def set_jersey_number(
    db: AsyncSession, team: Team, actor: User, target_user_id: uuid.UUID, jersey_number: int | None
) -> TeamMembership:
    # Unlike role changes, a captain/admin may set their own number — it carries no permissions.
    await require_role(db, team.id, actor, CAPTAIN_OR_ADMIN)
    target = await get_active_membership(db, team.id, target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    target.jersey_number = jersey_number
    await db.commit()
    await db.refresh(target)
    return target


async def remove_member(db: AsyncSession, team: Team, actor: User, target_user_id: uuid.UUID) -> None:
    actor_membership = await require_role(db, team.id, actor, CAPTAIN_OR_ADMIN)
    target = await get_active_membership(db, team.id, target_user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if target.role == TeamRole.CAPTAIN:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot remove the captain; transfer captaincy first"
        )
    if actor_membership.role == TeamRole.ADMIN and target.role == TeamRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "An admin cannot remove another admin")
    target.status = MembershipStatus.LEFT
    await db.commit()


async def leave_team(db: AsyncSession, team: Team, user: User) -> None:
    membership = await get_active_membership(db, team.id, user.id)
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not a member of this team")
    if membership.role == TeamRole.CAPTAIN:
        raise HTTPException(status.HTTP_409_CONFLICT, "Captain must transfer the role before leaving")
    membership.status = MembershipStatus.LEFT
    await db.commit()
