import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ApplicationDirection, ApplicationStatus, ListingStatus


class RosterSearchCreate(BaseModel):
    city: str


class RosterSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    city: str
    status: ListingStatus
    expires_at: datetime
    created_at: datetime


class RosterInviteCreate(BaseModel):
    """Captain/admin invites a specific player directly (no listing)."""

    user_id: uuid.UUID


class RosterApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    roster_search_id: uuid.UUID | None
    team_id: uuid.UUID
    user_id: uuid.UUID
    direction: ApplicationDirection
    status: ApplicationStatus
    created_at: datetime
