import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import PartyType, ReportStatus, str_enum


class Report(UUIDPKMixin, TimestampMixin, Base):
    """Separate from Feedback/Dispute: harassment/abuse/fake-profile issues."""

    __tablename__ = "reports"

    reporter_type: Mapped[PartyType] = mapped_column(str_enum(PartyType, length=8))
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    reported_type: Mapped[PartyType] = mapped_column(str_enum(PartyType, length=8))
    reported_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[ReportStatus] = mapped_column(
        str_enum(ReportStatus, length=16), default=ReportStatus.OPEN
    )
