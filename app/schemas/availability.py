import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ListingStatus, Sport


class PlayerAvailabilityCreate(BaseModel):
    sport: Sport
    city: str
    country: str | None = None
    region: str | None = None
    # Optional: falls back to the user's saved profile location (see User.latitude/longitude/
    # radius_km) if omitted. Publishing with an explicit value here also updates that saved
    # default, so it's remembered next time.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=200)


class PlayerAvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    sport: Sport
    city: str
    country: str | None
    region: str | None
    latitude: float | None
    longitude: float | None
    radius_km: float | None
    status: ListingStatus
    expires_at: datetime
    created_at: datetime
