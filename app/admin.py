"""SQLAdmin moderation/CRUD UI. Full access for all team members (no scoped roles for v1)."""

from fastapi import FastAPI
from sqladmin import Admin, ModelView

from app.db.session import engine
from app.models import (
    CreditTransaction,
    Dispute,
    Feedback,
    GameType,
    GuestApplication,
    GuestSearch,
    Match,
    MatchGuestParticipant,
    OpponentApplication,
    OpponentSearch,
    PlayerAvailability,
    Report,
    RosterApplication,
    RosterSearch,
    Team,
    TeamMembership,
    User,
)


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.name, User.phone, User.phone_verified, User.email]


class TeamAdmin(ModelView, model=Team):
    column_list = [
        Team.id,
        Team.name,
        Team.sport,
        Team.country,
        Team.city,
        Team.game_type_id,
        Team.completed,
        Team.is_adhoc,
    ]


class TeamMembershipAdmin(ModelView, model=TeamMembership):
    column_list = [TeamMembership.id, TeamMembership.team_id, TeamMembership.user_id, TeamMembership.role]


class GameTypeAdmin(ModelView, model=GameType):
    column_list = [GameType.id, GameType.sport, GameType.label]


class RosterSearchAdmin(ModelView, model=RosterSearch):
    column_list = [RosterSearch.id, RosterSearch.team_id, RosterSearch.city, RosterSearch.status]


class RosterApplicationAdmin(ModelView, model=RosterApplication):
    column_list = [RosterApplication.id, RosterApplication.direction, RosterApplication.status]


class OpponentSearchAdmin(ModelView, model=OpponentSearch):
    column_list = [OpponentSearch.id, OpponentSearch.team_id, OpponentSearch.city, OpponentSearch.status]


class OpponentApplicationAdmin(ModelView, model=OpponentApplication):
    column_list = [OpponentApplication.id, OpponentApplication.status]


class GuestSearchAdmin(ModelView, model=GuestSearch):
    column_list = [GuestSearch.id, GuestSearch.match_id, GuestSearch.status]


class GuestApplicationAdmin(ModelView, model=GuestApplication):
    column_list = [GuestApplication.id, GuestApplication.direction, GuestApplication.status]


class PlayerAvailabilityAdmin(ModelView, model=PlayerAvailability):
    column_list = [PlayerAvailability.id, PlayerAvailability.user_id, PlayerAvailability.status]


class MatchAdmin(ModelView, model=Match):
    column_list = [Match.id, Match.team_a_id, Match.team_b_id, Match.date, Match.status]


class MatchGuestParticipantAdmin(ModelView, model=MatchGuestParticipant):
    column_list = [MatchGuestParticipant.id, MatchGuestParticipant.match_id, MatchGuestParticipant.user_id]


class FeedbackAdmin(ModelView, model=Feedback):
    column_list = [Feedback.id, Feedback.match_id, Feedback.context, Feedback.rating]


class DisputeAdmin(ModelView, model=Dispute):
    column_list = [Dispute.id, Dispute.feedback_id, Dispute.status]


class ReportAdmin(ModelView, model=Report):
    column_list = [Report.id, Report.category, Report.status]


class CreditTransactionAdmin(ModelView, model=CreditTransaction):
    column_list = [
        CreditTransaction.id,
        CreditTransaction.user_id,
        CreditTransaction.amount,
        CreditTransaction.reason,
    ]


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(app, engine)
    for view in (
        UserAdmin,
        TeamAdmin,
        TeamMembershipAdmin,
        GameTypeAdmin,
        RosterSearchAdmin,
        RosterApplicationAdmin,
        OpponentSearchAdmin,
        OpponentApplicationAdmin,
        GuestSearchAdmin,
        GuestApplicationAdmin,
        PlayerAvailabilityAdmin,
        MatchAdmin,
        MatchGuestParticipantAdmin,
        FeedbackAdmin,
        DisputeAdmin,
        ReportAdmin,
        CreditTransactionAdmin,
    ):
        admin.add_view(view)
    return admin
