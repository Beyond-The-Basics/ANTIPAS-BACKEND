import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import MembershipStatus, TeamRole


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    role: TeamRole
    status: MembershipStatus
    joined_at: datetime


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
