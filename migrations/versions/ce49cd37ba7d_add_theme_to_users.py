"""Add theme to users

Client UI appearance preference (light/dark/system). Non-nullable with a server default so
existing rows backfill to "system", matching onboarding_completed/country's add-column pattern —
the model's Python-side default governs new rows once the server default is dropped.

Revision ID: ce49cd37ba7d
Revises: c336a7c1227e
Create Date: 2026-07-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ce49cd37ba7d"
down_revision: str | Sequence[str] | None = "c336a7c1227e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme", sa.String(length=16), nullable=False, server_default="system"),
    )
    op.alter_column("users", "theme", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "theme")
