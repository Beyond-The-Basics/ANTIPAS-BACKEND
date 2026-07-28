import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PitchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    price_per_hour: float | None = Field(default=None, gt=0)
    is_neutral: bool = False


class PitchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    name: str
    city: str
    price_per_hour: float | None
    is_neutral: bool
    created_at: datetime
