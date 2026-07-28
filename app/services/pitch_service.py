"""Pitch domain logic — the venue catalog a captain picks from when negotiating a match, instead
of typing a pitch name freehand every time. See `app/models/pitch.py` for how ownership vs.
`is_neutral` map to the negotiation UI's "your city"/"their city"/"neutral for both" labels."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pitch import Pitch
from app.models.search import OpponentApplication
from app.models.team import Team
from app.models.user import User
from app.schemas.pitch import PitchCreate
from app.services import opponent_service, team_service


async def create_pitch(db: AsyncSession, team: Team, actor: User, data: PitchCreate) -> Pitch:
    await team_service.require_role(db, team.id, actor, team_service.CAPTAIN_OR_ADMIN)
    pitch = Pitch(
        team_id=team.id,
        name=data.name,
        city=data.city,
        price_per_hour=data.price_per_hour,
        is_neutral=data.is_neutral,
    )
    db.add(pitch)
    await db.commit()
    await db.refresh(pitch)
    return pitch


async def list_pitches_for_negotiation(
    db: AsyncSession, application: OpponentApplication, actor: User
) -> list[Pitch]:
    """Pitches selectable in this negotiation: either team's own catalog, plus anyone's pitches
    marked neutral. Same auth as chat/proposals — only the two teams' captains/admins."""
    search = await opponent_service.get_search_or_404(db, application.opponent_search_id)
    await opponent_service.authorize_negotiation_member(db, application, actor)
    result = await db.scalars(
        select(Pitch)
        .where(
            or_(
                Pitch.team_id.in_((search.team_id, application.responding_team_id)),
                Pitch.is_neutral.is_(True),
            )
        )
        .order_by(Pitch.created_at)
    )
    return list(result)
