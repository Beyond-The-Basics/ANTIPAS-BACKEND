import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ListingStatus, Sport


class PlayerAvailabilityCreate(BaseModel):
    sport: Sport
    city: str


class PlayerAvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    sport: Sport
    city: str
    status: ListingStatus
    expires_at: datetime
    created_at: datetime
