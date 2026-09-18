import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.pitch import DEFAULT_COUNTRY


class PitchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    country: str = Field(default=DEFAULT_COUNTRY, min_length=1, max_length=60)
    city: str = Field(min_length=1, max_length=120)


class PitchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    country: str
    city: str
    created_at: datetime
