import uuid

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import CreditReason, SearchType


class CreditTransaction(UUIDPKMixin, TimestampMixin, Base):
    """Always tied to a User (never a Team; no shared pool)."""

    __tablename__ = "credit_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # signed: negative = charge, positive = credit
    reason: Mapped[CreditReason] = mapped_column(Enum(CreditReason, native_enum=False, length=32))
    related_search_type: Mapped[SearchType | None] = mapped_column(
        Enum(SearchType, native_enum=False, length=32), default=None
    )
    related_search_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
