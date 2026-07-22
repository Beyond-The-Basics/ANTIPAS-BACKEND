import enum


class Sport(enum.StrEnum):
    SOCCER = "soccer"
    TENNIS = "tennis"
    PADDLE = "paddle"


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
