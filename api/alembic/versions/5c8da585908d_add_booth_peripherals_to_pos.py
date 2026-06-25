"""add booth_peripherals to pos

Revision ID: 5c8da585908d
Revises: f0bd4bac1599
Create Date: 2026-04-27 16:39:50.805332

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5c8da585908d"
down_revision: str | None = "f0bd4bac1599"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pos",
        sa.Column(
            "booth_peripherals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("pos", "booth_peripherals")
