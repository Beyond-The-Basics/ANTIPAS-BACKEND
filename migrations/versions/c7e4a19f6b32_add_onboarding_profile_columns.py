"""Add onboarding profile columns to users

Backs the post-signup step wizard: nickname, age, country (default "Morocco"), city,
favorite_sports (multi-select), self-rated athletic characteristics (speed/strength/stamina/
agility, 1-5, all optional), and `onboarding_completed` — the flag the client uses to decide
whether a signed-in user still needs to go through the wizard.

Revision ID: c7e4a19f6b32
Revises: b41f8c7d2a05
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7e4a19f6b32"
down_revision: str | Sequence[str] | None = "b41f8c7d2a05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_COUNTRY = "Morocco"


def upgrade() -> None:
    op.add_column("users", sa.Column("nickname", sa.String(length=60), nullable=True))
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("country", sa.String(length=60), nullable=False, server_default=DEFAULT_COUNTRY),
    )
    op.add_column("users", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "favorite_sports",
            postgresql.ARRAY(sa.String(length=16)),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column("users", sa.Column("speed_rating", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("strength_rating", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("stamina_rating", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("agility_rating", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # The server_defaults above exist only to backfill existing rows; the model declares its own
    # Python-side defaults for new rows and doesn't need the column default any more.
    op.alter_column("users", "country", server_default=None)
    op.alter_column("users", "favorite_sports", server_default=None)
    op.alter_column("users", "onboarding_completed", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "agility_rating")
    op.drop_column("users", "stamina_rating")
    op.drop_column("users", "strength_rating")
    op.drop_column("users", "speed_rating")
    op.drop_column("users", "favorite_sports")
    op.drop_column("users", "city")
    op.drop_column("users", "country")
    op.drop_column("users", "age")
    op.drop_column("users", "nickname")
