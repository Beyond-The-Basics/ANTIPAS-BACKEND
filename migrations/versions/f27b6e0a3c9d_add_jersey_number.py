"""Add jersey_number to team_memberships

Captain/admin-assigned, shown on the team's lineup card. Nullable — most memberships won't have
one until a captain sets it, and it's never required for anything (completion gating is roster
count only, from team_memberships + game_types.players_per_side).

Revision ID: f27b6e0a3c9d
Revises: e5a1c9d4f6b8
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f27b6e0a3c9d"
down_revision: str | Sequence[str] | None = "e5a1c9d4f6b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("team_memberships", sa.Column("jersey_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("team_memberships", "jersey_number")
