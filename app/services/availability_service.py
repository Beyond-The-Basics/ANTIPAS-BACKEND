"""PlayerAvailability domain logic (Flow 1 individual broadcast).

An individual broadcasts "available for [sport] in [city]" so teams can discover and invite them.
Free to publish (no credit charge). Teams that find a player this way invite them through the
existing RosterApplication / GuestApplication `team_invited` flow — this listing is discovery only.

The player shares a map location and chooses a privacy radius: they're only discoverable by a
searcher whose search point falls within that radius. A searcher may additionally scope their own
search radius; a listing must satisfy both distances to appear (mutual constraint).
"""

import math
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import ListingStatus, Sport
from app.models.search import PlayerAvailability
from app.models.user import User

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


async def get_or_404(db: AsyncSession, availability_id: uuid.UUID) -> PlayerAvailability:
    availability = await db.get(PlayerAvailability, availability_id)
    if availability is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Availability not found")
    return availability


async def publish(
    db: AsyncSession,
    user: User,
    sport: Sport,
    city: str,
    latitude: float | None,
    longitude: float | None,
    radius_km: float | None,
    country: str | None = None,
    region: str | None = None,
) -> PlayerAvailability:
    # Fall back to the user's saved profile location when the request omits it, so a player only
    # has to set it once (either on first publish or from their profile) and can reuse it after.
    resolved_lat = latitude if latitude is not None else user.latitude
    resolved_lng = longitude if longitude is not None else user.longitude
    resolved_radius = radius_km if radius_km is not None else user.radius_km
    if resolved_lat is None or resolved_lng is None or resolved_radius is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Location and radius are required — set them in your profile or when publishing",
        )

    # Publishing with an explicit location also saves it as the user's new default.
    user.latitude = resolved_lat
    user.longitude = resolved_lng
    user.radius_km = resolved_radius

    availability = PlayerAvailability(
        user_id=user.id,
        sport=sport,
        city=city,
        country=country,
        region=region,
        latitude=resolved_lat,
        longitude=resolved_lng,
        radius_km=resolved_radius,
        status=ListingStatus.OPEN,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.listing_expiry_hours),
    )
    db.add(availability)
    await db.commit()
    await db.refresh(availability)
    return availability


async def list_availabilities(
    db: AsyncSession,
    sport: Sport | None,
    city: str | None,
    limit: int,
    offset: int,
    country: str | None = None,
    search_lat: float | None = None,
    search_lng: float | None = None,
    search_radius_km: float | None = None,
) -> list[PlayerAvailability]:
    stmt = select(PlayerAvailability).where(PlayerAvailability.status == ListingStatus.OPEN)
    if sport is not None:
        stmt = stmt.where(PlayerAvailability.sport == sport)
    if city is not None:
        stmt = stmt.where(PlayerAvailability.city == city)
    if country is not None:
        stmt = stmt.where(PlayerAvailability.country == country)

    if search_lat is None or search_lng is None:
        result = await db.scalars(stmt.limit(limit).offset(offset))
        return list(result)

    # Distance filtering can't happen in SQL without PostGIS, so pull the (already sport/city
    # scoped) candidates, filter by distance in Python, then paginate the filtered set.
    result = await db.scalars(stmt)
    visible = []
    for availability in result:
        if availability.latitude is None or availability.longitude is None:
            continue
        distance = haversine_km(search_lat, search_lng, availability.latitude, availability.longitude)
        if availability.radius_km is not None and distance > availability.radius_km:
            continue
        if search_radius_km is not None and distance > search_radius_km:
            continue
        visible.append(availability)
    return visible[offset : offset + limit]


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
