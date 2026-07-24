"""Add password auth columns to users

Adds the two columns JWT email+password auth needs:
- `password_hash` — bcrypt digest, nullable because users created before auth (and via the
  dev-only `POST /users`) have no credential and simply cannot log in.
- `email_verified` — mirrors the existing `phone_verified`, for the email OTP step that comes next.

`email` deliberately stays nullable here. It is required by the signup schema, so every account
that can log in has one, but forcing NOT NULL would break existing rows with no email.

Revision ID: b41f8c7d2a05
Revises: 9a72b3e127e9
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b41f8c7d2a05"
down_revision: str | Sequence[str] | None = "9a72b3e127e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=128), nullable=True))
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # The server_default exists only to backfill existing rows; the model doesn't declare one.
    op.alter_column("users", "email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "email_verified")
    op.drop_column("users", "password_hash")
