import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MatchStatus, Sport


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opponent_search_id: uuid.UUID
    team_a_id: uuid.UUID
    team_b_id: uuid.UUID
    sport: Sport
    game_type_id: uuid.UUID
    city: str
    pitch: str
    date: datetime
    status: MatchStatus
    created_at: datetime
