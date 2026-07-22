import uuid

from sqlalchemy import ARRAY, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import DisputeStatus, FeedbackContext, PartyType, str_enum


class Feedback(UUIDPKMixin, TimestampMixin, Base):
    """Opponent-vs-opponent, opponent-vs-individual, or the host-team<->guest loop. Visible immediately."""

    __tablename__ = "feedback"

    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), index=True)
    context: Mapped[FeedbackContext] = mapped_column(str_enum(FeedbackContext, length=16))
    from_type: Mapped[PartyType] = mapped_column(str_enum(PartyType, length=8))
    from_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    to_type: Mapped[PartyType] = mapped_column(str_enum(PartyType, length=8))
    to_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    rating: Mapped[int] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    comment: Mapped[str | None] = mapped_column(Text, default=None)


class Dispute(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "disputes"

    feedback_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("feedback.id"), index=True)
    raised_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[DisputeStatus] = mapped_column(
        str_enum(DisputeStatus, length=24), default=DisputeStatus.OPEN
    )
