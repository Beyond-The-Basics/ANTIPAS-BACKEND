import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ApplicationDirection, ApplicationStatus, ListingStatus


class GuestSearchCreate(BaseModel):
    # Which side of the match is short a player (must be one of the match's two teams).
    team_id: uuid.UUID


class GuestSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    team_id: uuid.UUID
    city: str
    status: ListingStatus
    expires_at: datetime
    created_at: datetime


class GuestInviteCreate(BaseModel):
    team_id: uuid.UUID
    user_id: uuid.UUID


class GuestApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    guest_search_id: uuid.UUID | None
    match_id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    direction: ApplicationDirection
    status: ApplicationStatus
    created_at: datetime


class MatchGuestParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    team_id: uuid.UUID
    user_id: uuid.UUID
    guest_application_id: uuid.UUID
    created_at: datetime
