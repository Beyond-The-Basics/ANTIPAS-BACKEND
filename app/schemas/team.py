import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import Sport


class TeamCreate(BaseModel):
    name: str
    sport: Sport
    logo_url: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    # Captain-declared completion flag that gates opponent search (Flow 2).
    completed: bool | None = None


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    logo_url: str | None
    sport: Sport
    completed: bool
    is_adhoc: bool
    created_at: datetime
