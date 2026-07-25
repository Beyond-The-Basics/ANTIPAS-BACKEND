import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import MembershipStatus, TeamRole

MIN_JERSEY_NUMBER = 0
MAX_JERSEY_NUMBER = 99


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: TeamRole
    status: MembershipStatus
    jersey_number: int | None
    joined_at: datetime


class JerseyNumberUpdate(BaseModel):
    jersey_number: int | None = Field(default=None, ge=MIN_JERSEY_NUMBER, le=MAX_JERSEY_NUMBER)


class RoleUpdate(BaseModel):
    """Promote/demote between admin and member. Captaincy changes go through transfer-captain."""

    role: TeamRole

    @field_validator("role")
    @classmethod
    def not_captain(cls, v: TeamRole) -> TeamRole:
        if v == TeamRole.CAPTAIN:
            raise ValueError("Use the transfer-captain endpoint to change the captain.")
        return v


class TransferCaptain(BaseModel):
    new_captain_user_id: uuid.UUID
