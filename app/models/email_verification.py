import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin


class EmailVerification(UUIDPKMixin, TimestampMixin, Base):
    """The one live email-verification challenge for a user.

    `user_id` is unique, which is how "only one active OTP per user" is enforced in the schema
    rather than by convention — requesting a new code deletes the old row before inserting.

    `email` records the address the code was actually sent to. It is not redundant with
    `users.email`: someone can change their address again while a code is in flight, and a code
    mailed to the previous address must not verify the new one.

    Rows are short-lived by design. They're deleted on success, on exhausting the attempt cap, and
    by the periodic sweep in `app/workers/tasks.py` once expired.
    """

    __tablename__ = "email_verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    email: Mapped[str] = mapped_column(String(255))
    # bcrypt digest of the 6-digit code — the raw code exists only in the email that was sent.
    otp_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
