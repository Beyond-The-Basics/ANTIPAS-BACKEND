import uuid

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import CreditReason, SearchType, str_enum


class CreditTransaction(UUIDPKMixin, TimestampMixin, Base):
    """Always tied to a User (never a Team; no shared pool)."""

    __tablename__ = "credit_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # signed: negative = charge, positive = credit
    reason: Mapped[CreditReason] = mapped_column(str_enum(CreditReason, length=32))
    related_search_type: Mapped[SearchType | None] = mapped_column(
        str_enum(SearchType, length=32), default=None
    )
    related_search_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
