import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.pitch import PitchCreate, PitchRead
from app.services import opponent_service, pitch_service, team_service

router = APIRouter(tags=["pitches"])


@router.post(
    "/teams/{team_id}/pitches",
    response_model=PitchRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_pitch(
    team_id: uuid.UUID,
    data: PitchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await pitch_service.create_pitch(db, team, current_user, data)


@router.get(
    "/opponent-applications/{application_id}/pitches",
    response_model=list[PitchRead],
)
async def list_pitches_for_negotiation(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    return await pitch_service.list_pitches_for_negotiation(db, application, current_user)
