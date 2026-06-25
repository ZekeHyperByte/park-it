"""Convert barcode global-unique index to partial-unique-while-active.

A globally unique barcode index blocks ever reusing a ticket number across
separate (completed) stays — e.g. a ticket printer that cycles through a finite
sequence would eventually fail to create an entry transaction. Mirror the
card_number scheme: enforce uniqueness only among ACTIVE transactions.

Revision ID: b8c9d0e1f2a3
Revises: f7999809b648
Create Date: 2026-06-04
"""


import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "f7999809b648"
branch_labels = None
depends_on = None

_ACTIVE_BARCODE = "status = 'ACTIVE' AND barcode IS NOT NULL"


def upgrade() -> None:
    # Drop the old globally-unique index on barcode.
    op.drop_index("ix_parking_transactions_barcode", table_name="parking_transactions")
    # Recreate a plain (non-unique) index for fast lookups.
    op.create_index(
        "ix_parking_transactions_barcode",
        "parking_transactions",
        ["barcode"],
        unique=False,
    )
    # Partial unique index: only one ACTIVE transaction per barcode.
    op.create_index(
        "uq_active_barcode",
        "parking_transactions",
        ["barcode"],
        unique=True,
        postgresql_where=sa.text(_ACTIVE_BARCODE),
    )


def downgrade() -> None:
    op.drop_index("uq_active_barcode", table_name="parking_transactions")
    op.drop_index("ix_parking_transactions_barcode", table_name="parking_transactions")
    op.create_index(
        "ix_parking_transactions_barcode",
        "parking_transactions",
        ["barcode"],
        unique=True,
    )
