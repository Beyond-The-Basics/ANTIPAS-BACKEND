import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus, ListingStatus, Sport


class OpponentSearchCreate(BaseModel):
    # No game_type_id here — the search inherits the publishing team's own game_type_id (set at
    # the roster-building stage, required for `team.completed`), rather than asking again.
    city: str
    country: str | None = None
    pitch: str
    date: datetime  # full date + time kickoff (the initial, negotiable proposal)


class OpponentSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    sport: Sport
    game_type_id: uuid.UUID
    city: str
    country: str | None
    pitch: str
    date: datetime
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
    # Current negotiation proposal (present once the challenge is accepted).
    proposed_date: datetime | None
    proposed_pitch: str | None
    proposed_by_team_id: uuid.UUID | None
    created_at: datetime


class ProposeTerms(BaseModel):
    """Either captain proposes a kickoff time and pitch during the negotiation."""

    date: datetime
    pitch: str = Field(min_length=1, max_length=255)


class NegotiationMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class NegotiationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opponent_application_id: uuid.UUID
    sender_user_id: uuid.UUID
    body: str
    created_at: datetime
