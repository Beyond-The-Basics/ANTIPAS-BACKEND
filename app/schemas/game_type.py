import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import Sport


class GameTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sport: Sport
    label: str
    players_per_side: int
