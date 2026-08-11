"""Narrow pitches to a city venue directory

A pitch turned out to be a venue in a city, not a team's property: teams pick a country and a city
and choose from whatever is there. So team ownership goes (`team_id`, and `is_neutral` with it,
since "offer my pitch to the opponent too" is meaningless once nobody owns one), and so does
everything the Places export carried that nothing selects on — district, coordinates, phone, maps
link, price.

`place_id` was the seeder's idempotency key; `(name, country, city)` unique replaces it, and also
stops a captain's hand-added venue from duplicating a seeded one.

Revision ID: c23f8c313e20
Revises: c92e4a7d1b83
Create Date: 2026-08-11

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c23f8c313e20"
down_revision: Union[str, Sequence[str], None] = "c92e4a7d1b83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default so the NOT NULL add succeeds against existing rows; dropped immediately after,
    # so the model's Python-side default governs new ones (same pattern as a7c31f9b04e2).
    op.add_column(
        "pitches", sa.Column("country", sa.String(length=60), nullable=False, server_default="Morocco")
    )
    op.alter_column("pitches", "country", server_default=None)
    op.create_index("ix_pitches_country", "pitches", ["country"])

    op.drop_index("ix_pitches_place_id", table_name="pitches")
    op.drop_column("pitches", "place_id")
    op.drop_column("pitches", "maps_url")
    op.drop_column("pitches", "phone")
    op.drop_column("pitches", "longitude")
    op.drop_column("pitches", "latitude")
    op.drop_column("pitches", "district")
    op.drop_column("pitches", "price_per_hour")
    op.drop_column("pitches", "is_neutral")
    # Drops the FK to teams along with the column.
    op.drop_column("pitches", "team_id")

    op.create_unique_constraint(
        "uq_pitches_name_country_city", "pitches", ["name", "country", "city"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_pitches_name_country_city", "pitches", type_="unique")

    # All restored as nullable: the values are gone, and `team_id` in particular cannot be
    # reconstructed — which team once owned a venue is not derivable from anything left.
    op.add_column("pitches", sa.Column("team_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("pitches_team_id_fkey", "pitches", "teams", ["team_id"], ["id"])
    op.create_index("ix_pitches_team_id", "pitches", ["team_id"])
    op.add_column(
        "pitches", sa.Column("is_neutral", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("pitches", sa.Column("price_per_hour", sa.Float(), nullable=True))
    op.add_column("pitches", sa.Column("district", sa.String(length=160), nullable=True))
    op.add_column("pitches", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("pitches", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("pitches", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("pitches", sa.Column("maps_url", sa.String(length=512), nullable=True))
    op.add_column("pitches", sa.Column("place_id", sa.String(length=128), nullable=True))
    op.create_index("ix_pitches_place_id", "pitches", ["place_id"], unique=True)

    op.drop_index("ix_pitches_country", table_name="pitches")
    op.drop_column("pitches", "country")
