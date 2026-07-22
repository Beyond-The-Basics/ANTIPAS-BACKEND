"""PlayerAvailability domain logic (Flow 1 individual broadcast).

An individual broadcasts "available for [sport] in [city]" so teams can discover and invite them.
Free to publish (no credit charge). Teams that find a player this way invite them through the
existing RosterApplication / GuestApplication `team_invited` flow — this listing is discovery only.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ListingStatus, Sport
from app.models.search import PlayerAvailability
from app.models.user import User


async def get_or_404(db: AsyncSession, availability_id: uuid.UUID) -> PlayerAvailability:
    availability = await db.get(PlayerAvailability, availability_id)
    if availability is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Availability not found")
    return availability


async def publish(db: AsyncSession, user: User, sport: Sport, city: str) -> PlayerAvailability:
    availability = PlayerAvailability(
        user_id=user.id,
        sport=sport,
        city=city,
        status=ListingStatus.OPEN,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.listing_expiry_hours),
    )
    db.add(availability)
    await db.commit()
    await db.refresh(availability)
    return availability


async def list_availabilities(
    db: AsyncSession, sport: Sport | None, city: str | None, limit: int, offset: int
) -> list[PlayerAvailability]:
    stmt = select(PlayerAvailability).where(PlayerAvailability.status == ListingStatus.OPEN)
    if sport is not None:
        stmt = stmt.where(PlayerAvailability.sport == sport)
    if city is not None:
        stmt = stmt.where(PlayerAvailability.city == city)
    result = await db.scalars(stmt.limit(limit).offset(offset))
    return list(result)


async def list_mine(db: AsyncSession, user: User) -> list[PlayerAvailability]:
    result = await db.scalars(select(PlayerAvailability).where(PlayerAvailability.user_id == user.id))
    return list(result)


async def withdraw(db: AsyncSession, availability: PlayerAvailability, actor: User) -> None:
    if availability.user_id != actor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can withdraw this availability")
    if availability.status != ListingStatus.OPEN:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Availability is not open")
    availability.status = ListingStatus.WITHDRAWN
    await db.commit()
