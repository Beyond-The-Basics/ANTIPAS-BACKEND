import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ApplicationStatus, ListingStatus, Sport


class OpponentSearchCreate(BaseModel):
    game_type_id: uuid.UUID
    city: str
    pitch: str
    date: date


class OpponentSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    sport: Sport
    game_type_id: uuid.UUID
    city: str
    pitch: str
    date: date
    status: ListingStatus
    expires_at: datetime
    created_at: datetime


class OpponentApplicationCreate(BaseModel):
    responding_team_id: uuid.UUID


class OpponentApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opponent_search_id: uuid.UUID
    responding_team_id: uuid.UUID
    status: ApplicationStatus
    created_at: datetime
