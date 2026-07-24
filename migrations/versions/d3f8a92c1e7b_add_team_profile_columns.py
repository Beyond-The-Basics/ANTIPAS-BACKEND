"""Add team profile columns

Adds description, country (default "Morocco", matching users.country), and city to teams — the
info a captain fills in beyond name/sport/logo_url. All nullable except country, same reasoning
as the users table: no captain-facing form should ever crash on a missing value.

Revision ID: d3f8a92c1e7b
Revises: c7e4a19f6b32
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f8a92c1e7b"
down_revision: str | Sequence[str] | None = "c7e4a19f6b32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_COUNTRY = "Morocco"


def upgrade() -> None:
    op.add_column("teams", sa.Column("description", sa.String(length=500), nullable=True))
    op.add_column(
        "teams",
        sa.Column("country", sa.String(length=60), nullable=False, server_default=DEFAULT_COUNTRY),
    )
    op.add_column("teams", sa.Column("city", sa.String(length=120), nullable=True))
    # The server_default exists only to backfill existing rows; the model declares its own
    # Python-side default for new rows and doesn't need the column default any more.
    op.alter_column("teams", "country", server_default=None)


def downgrade() -> None:
    op.drop_column("teams", "city")
    op.drop_column("teams", "country")
    op.drop_column("teams", "description")
