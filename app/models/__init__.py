"""Import all models here so Alembic autogenerate and SQLAdmin can discover them."""

from app.db.base_class import Base
from app.models.credit import CreditTransaction
from app.models.feedback import Dispute, Feedback
from app.models.game_type import GameType
from app.models.match import Match, MatchGuestParticipant
from app.models.moderation import Report
from app.models.pitch import Pitch
from app.models.search import (
    GuestApplication,
    GuestSearch,
    NegotiationMessage,
    NegotiationProposal,
    OpponentApplication,
    OpponentSearch,
    PlayerAvailability,
    RosterApplication,
    RosterSearch,
)
from app.models.team import Team, TeamMembership
from app.models.user import User

__all__ = [
    "Base",
    "CreditTransaction",
    "Dispute",
    "Feedback",
    "GameType",
    "GuestApplication",
    "GuestSearch",
    "Match",
    "MatchGuestParticipant",
    "NegotiationMessage",
    "NegotiationProposal",
    "OpponentApplication",
    "OpponentSearch",
    "Pitch",
    "PlayerAvailability",
    "Report",
    "RosterApplication",
    "RosterSearch",
    "Team",
    "TeamMembership",
    "User",
]
