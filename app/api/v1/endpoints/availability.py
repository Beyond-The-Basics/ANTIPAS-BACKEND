import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_verified_user
from app.db.session import get_db
from app.models.enums import Sport
from app.models.user import User
from app.schemas.availability import PlayerAvailabilityCreate, PlayerAvailabilityRead
from app.services import availability_service

router = APIRouter(tags=["availability"])


@router.post(
    "/player-availability",
    response_model=PlayerAvailabilityRead,
    status_code=status.HTTP_201_CREATED,
)
async def publish_availability(
    data: PlayerAvailabilityCreate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await availability_service.publish(
        db,
        current_user,
        data.sport,
        data.city,
        data.latitude,
        data.longitude,
        data.radius_km,
        data.country,
        data.region,
    )


@router.get("/player-availability", response_model=list[PlayerAvailabilityRead])
async def browse_availability(
    sport: Sport | None = None,
    city: str | None = None,
    country: str | None = None,
    limit: int = 50,
    offset: int = 0,
    search_lat: float | None = None,
    search_lng: float | None = None,
    search_radius_km: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await availability_service.list_availabilities(
        db, sport, city, limit, offset, country, search_lat, search_lng, search_radius_km
    )


@router.get("/users/me/availability", response_model=list[PlayerAvailabilityRead])
async def list_my_availability(
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await availability_service.list_mine(db, current_user)


@router.get("/player-availability/{availability_id}", response_model=PlayerAvailabilityRead)
async def get_availability(availability_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await availability_service.get_or_404(db, availability_id)


@router.post(
    "/player-availability/{availability_id}/withdraw",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def withdraw_availability(
    availability_id: uuid.UUID,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
):
    availability = await availability_service.get_or_404(db, availability_id)
    await availability_service.withdraw(db, availability, current_user)
