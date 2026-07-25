import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Sport

MAX_DESCRIPTION_LENGTH = 500


class TeamCreate(BaseModel):
    name: str
    sport: Sport
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    logo_url: str | None = None
    # Optional at create — the service defaults it to "Morocco", same as a user's onboarding
    # profile, so a captain who skips the location step still has a valid team.
    country: str | None = Field(default=None, min_length=1, max_length=60)
    city: str | None = Field(default=None, min_length=1, max_length=120)


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    logo_url: str | None = None
    country: str | None = Field(default=None, min_length=1, max_length=60)
    city: str | None = Field(default=None, min_length=1, max_length=120)
    # The lineup format (e.g. 7v7) — set at the roster-building stage, never at creation. Must
    # belong to the team's own sport; see team_service.update_team.
    game_type_id: uuid.UUID | None = None
    # Captain-declared completion flag that gates opponent search (Flow 2). Setting it True
    # requires game_type_id to already be set (on this call or a prior one) and the active roster
    # to reach that game type's players_per_side.
    completed: bool | None = None


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    logo_url: str | None
    country: str
    city: str | None
    sport: Sport
    game_type_id: uuid.UUID | None
    completed: bool
    is_adhoc: bool
    created_at: datetime
