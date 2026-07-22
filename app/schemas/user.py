import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    phone: str
    phone_verified: bool
    email: str | None
    created_at: datetime
