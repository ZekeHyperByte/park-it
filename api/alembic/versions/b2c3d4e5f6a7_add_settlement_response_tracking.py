"""add settlement response tracking columns

Adds the columns required by the Multibank v1.3 §II response handling pipeline:

emoney_settlements:
  - uploaded_at (timestamp): when SFTP upload succeeded
  - response_received_at (timestamp): when .OK/.NOK was fetched
  - response_extension (varchar(4)): "OK" or "NOK"

emoney_transactions:
  - bank_response_status (varchar(2)): per-row status code (00, 02, 04, ...)
  - bank_response_at (timestamp): when the bank result was applied

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-08

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "emoney_settlements",
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "emoney_settlements",
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "emoney_settlements",
        sa.Column("response_extension", sa.String(length=4), nullable=True),
    )

    op.add_column(
        "emoney_transactions",
        sa.Column("bank_response_status", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "emoney_transactions",
        sa.Column("bank_response_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("emoney_transactions", "bank_response_at")
    op.drop_column("emoney_transactions", "bank_response_status")
    op.drop_column("emoney_settlements", "response_extension")
    op.drop_column("emoney_settlements", "response_received_at")
    op.drop_column("emoney_settlements", "uploaded_at")
