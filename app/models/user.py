from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.team import TeamMembership


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    phone_verified: Mapped[bool] = mapped_column(default=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, default=None)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, default=None)

    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="user")
