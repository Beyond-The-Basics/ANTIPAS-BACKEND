"""Widen pitches for the public venue directory

The catalog was team-owned only. Seeding a real city directory (Casablanca, 72 venues from a
Places export) needs venues that belong to nobody, so `team_id` becomes nullable, and needs the
fields the broadcast wizard's pitch rows actually render: district, coordinates for the distance
readout, phone and maps link for whoever ends up booking, and `place_id` as the idempotency key.

Revision ID: c92e4a7d1b83
Revises: a7c31f9b04e2
Create Date: 2026-08-03

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c92e4a7d1b83"
down_revision: Union[str, Sequence[str], None] = "a7c31f9b04e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("pitches", "team_id", existing_type=sa.UUID(as_uuid=True), nullable=True)
    # Directory names run longer than a captain's own shorthand ("Terrain de foot de proximite
    # Sidi Othmane (Av. Mohamed Bouziane)" is 64 chars).
    op.alter_column(
        "pitches", "name", existing_type=sa.String(length=120), type_=sa.String(length=160)
    )
    op.add_column("pitches", sa.Column("district", sa.String(length=160), nullable=True))
    op.add_column("pitches", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("pitches", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("pitches", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("pitches", sa.Column("maps_url", sa.String(length=512), nullable=True))
    op.add_column("pitches", sa.Column("place_id", sa.String(length=128), nullable=True))
    op.create_index("ix_pitches_place_id", "pitches", ["place_id"], unique=True)
    op.create_index("ix_pitches_city", "pitches", ["city"])


def downgrade() -> None:
    op.drop_index("ix_pitches_city", table_name="pitches")
    op.drop_index("ix_pitches_place_id", table_name="pitches")
    op.drop_column("pitches", "place_id")
    op.drop_column("pitches", "maps_url")
    op.drop_column("pitches", "phone")
    op.drop_column("pitches", "longitude")
    op.drop_column("pitches", "latitude")
    op.drop_column("pitches", "district")
    op.alter_column(
        "pitches", "name", existing_type=sa.String(length=160), type_=sa.String(length=120)
    )
    # Directory venues have no owner and cannot satisfy the restored NOT NULL; they only exist
    # because of this revision, so dropping them is the correct inverse.
    op.execute("DELETE FROM pitches WHERE team_id IS NULL")
    op.alter_column("pitches", "team_id", existing_type=sa.UUID(as_uuid=True), nullable=False)
