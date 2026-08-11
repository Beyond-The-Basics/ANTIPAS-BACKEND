"""Add broadcast terms to opponent_searches

The broadcast wizard publishes five negotiable terms rather than the two the table held. Date and
pitch already existed; this adds the alternate date, the time-negotiable flag, the registered-venue
reference, the booking mode, and the publisher's note.

`pitch` also becomes nullable: "let the opponent choose" publishes a challenge with no venue, which
is a legitimate broadcast rather than incomplete data.

Revision ID: a7c31f9b04e2
Revises: 134dd592cece
Create Date: 2026-08-03

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c31f9b04e2"
down_revision: Union[str, Sequence[str], None] = "134dd592cece"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "opponent_searches", sa.Column("pitch_id", sa.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_opponent_searches_pitch_id_pitches",
        "opponent_searches",
        "pitches",
        ["pitch_id"],
        ["id"],
    )
    op.add_column(
        "opponent_searches", sa.Column("date_alt", sa.DateTime(timezone=True), nullable=True)
    )
    # server_default so the NOT NULL add succeeds against existing rows; the model carries the
    # Python-side default for new ones.
    op.add_column(
        "opponent_searches",
        sa.Column("time_open", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "opponent_searches",
        sa.Column(
            "booking_mode",
            sa.String(length=16),
            nullable=False,
            server_default="we_book",
        ),
    )
    op.add_column("opponent_searches", sa.Column("note", sa.String(length=500), nullable=True))
    op.alter_column("opponent_searches", "pitch", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    # Rows published with "let the opponent choose" have no venue name, so they cannot satisfy the
    # restored NOT NULL. Give them a placeholder rather than letting the downgrade fail outright.
    op.execute("UPDATE opponent_searches SET pitch = 'TBD' WHERE pitch IS NULL")
    op.alter_column("opponent_searches", "pitch", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("opponent_searches", "note")
    op.drop_column("opponent_searches", "booking_mode")
    op.drop_column("opponent_searches", "time_open")
    op.drop_column("opponent_searches", "date_alt")
    op.drop_constraint(
        "fk_opponent_searches_pitch_id_pitches", "opponent_searches", type_="foreignkey"
    )
    op.drop_column("opponent_searches", "pitch_id")
