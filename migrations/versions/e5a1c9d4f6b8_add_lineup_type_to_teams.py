"""Add lineup type (GameType) to teams, and players_per_side to game_types

Backs the roster-building lineup step: a captain declares a GameType for the team (e.g. 7v7),
which then gates `completed` on the active roster reaching `players_per_side`, and is inherited
by any OpponentSearch the team later publishes instead of being chosen again there.

`game_types.players_per_side` is added NOT NULL, so existing rows (from `db/seed.py`'s catalog)
are backfilled by label before the constraint is applied. `teams.game_type_id` is nullable —
existing teams simply have no lineup set until a captain picks one.

Revision ID: e5a1c9d4f6b8
Revises: d3f8a92c1e7b
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5a1c9d4f6b8"
down_revision: str | Sequence[str] | None = "d3f8a92c1e7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Matches app/db/seed.py's GAME_TYPE_CATALOG at the time this migration was written.
PLAYERS_PER_SIDE_BY_LABEL = {
    "5v5": 5,
    "6v6": 6,
    "7v7": 7,
    "11v11": 11,
    "singles": 1,
    "doubles": 2,
}


def upgrade() -> None:
    op.add_column("game_types", sa.Column("players_per_side", sa.Integer(), nullable=True))
    for label, count in PLAYERS_PER_SIDE_BY_LABEL.items():
        op.execute(
            sa.text("UPDATE game_types SET players_per_side = :count WHERE label = :label").bindparams(
                count=count, label=label
            )
        )
    op.alter_column("game_types", "players_per_side", nullable=False)

    op.add_column(
        "teams",
        sa.Column("game_type_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_teams_game_type_id_game_types",
        "teams",
        "game_types",
        ["game_type_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_teams_game_type_id_game_types", "teams", type_="foreignkey")
    op.drop_column("teams", "game_type_id")
    op.drop_column("game_types", "players_per_side")
