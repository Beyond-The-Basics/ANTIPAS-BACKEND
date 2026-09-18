from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.pitch import DEFAULT_COUNTRY
from app.models.user import User
from app.schemas.pitch import PitchCreate, PitchRead
from app.services import pitch_service

router = APIRouter(tags=["pitches"])


@router.get("/pitches", response_model=list[PitchRead])
async def list_pitches(
    country: str = Query(default=DEFAULT_COUNTRY),
    city: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """The venue directory, scoped to a country and usually one city — how a team picks a pitch."""
    return await pitch_service.list_pitches(db, country, city)


@router.post("/pitches", response_model=PitchRead, status_code=status.HTTP_201_CREATED)
async def create_pitch(
    data: PitchCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a venue the directory doesn't have yet. No team scoping — anyone who plays there can
    add it, and it's shared with everyone.

    Re-adding an existing venue returns that row rather than a duplicate, so this is safe to call
    optimistically; it answers 200 in that case, keeping 201 honest about having created something.
    """
    pitch, created = await pitch_service.get_or_create_pitch(db, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return pitch
