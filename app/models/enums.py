import enum

from sqlalchemy import Enum as SAEnum


def str_enum(enum_cls: type[enum.StrEnum], length: int = 32) -> SAEnum:
    """SQLAlchemy column type for a StrEnum that stores the member *value* (e.g. "soccer"),
    not the member *name* ("SOCCER"), as a VARCHAR (no native Postgres enum type)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
    )


class Sport(enum.StrEnum):
    SOCCER = "soccer"
    TENNIS = "tennis"
    PADDLE = "paddle"
    BASKETBALL = "basketball"


class Gender(enum.StrEnum):
    MALE = "male"
    FEMALE = "female"


class Locale(enum.StrEnum):
    EN = "en"
    FR = "fr"
    AR = "ar"


class TeamRole(enum.StrEnum):
    CAPTAIN = "captain"
    ADMIN = "admin"
    MEMBER = "member"


class MembershipStatus(enum.StrEnum):
    ACTIVE = "active"
    LEFT = "left"


class ListingStatus(enum.StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    CONFIRMED = "confirmed"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ApplicationDirection(enum.StrEnum):
    PLAYER_APPLIED = "player_applied"
    TEAM_INVITED = "team_invited"


class ApplicationStatus(enum.StrEnum):
    PENDING = "pending"
    # An opponent challenge the publisher accepted: the two teams are now negotiating date/time/
    # pitch in chat. Becomes CONFIRMED when they agree and a Match is created.
    ACCEPTED = "accepted"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class MatchStatus(enum.StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED_BY_A = "cancelled_by_a"
    CANCELLED_BY_B = "cancelled_by_b"
    PLAYED = "played"


class FeedbackContext(enum.StrEnum):
    OPPONENT = "opponent"
    HOST_GUEST = "host_guest"


class PartyType(enum.StrEnum):
    USER = "user"
    TEAM = "team"


class DisputeStatus(enum.StrEnum):
    OPEN = "open"
    RESOLVED_REMOVED = "resolved_removed"
    RESOLVED_UPHELD = "resolved_upheld"


class ReportStatus(enum.StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CreditReason(enum.StrEnum):
    PUBLISH_CHARGE = "publish_charge"
    REFUND_NONENGAGEMENT = "refund_nonengagement"
    TOPUP = "topup"
    PURCHASE = "purchase"


class SearchType(enum.StrEnum):
    ROSTER_SEARCH = "roster_search"
    OPPONENT_SEARCH = "opponent_search"
    GUEST_SEARCH = "guest_search"
    PLAYER_AVAILABILITY = "player_availability"
