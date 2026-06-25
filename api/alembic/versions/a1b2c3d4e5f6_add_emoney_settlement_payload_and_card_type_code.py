"""add settlement_payload_hex and card_type_code to emoney_transactions

Adds two columns required by the Multibank v1.3 settlement spec:

- settlement_payload_hex (Text): the deduct response body from cardtype through
  CardLog Transaction (per Multibank v1.3 §I "Settlement data Transaction").
  This is what gets written verbatim to the settlement file. Distinct from
  raw_response_hex which contains the full PASSTI frame (incl STX/LEN/LRC)
  used only for debugging.

- card_type_code (int): PASSTI card type code per V1.12 §V. 0x09 = QR Payment,
  which Multibank v1.3 explicitly excludes from bank settlement. Indexed for
  fast settlement-worker filter.

Revision ID: a1b2c3d4e5f6
Revises: 5c8da585908d
Create Date: 2026-05-08

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "5c8da585908d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "emoney_transactions",
        sa.Column("settlement_payload_hex", sa.Text(), nullable=True),
    )
    op.add_column(
        "emoney_transactions",
        sa.Column("card_type_code", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_emoney_transactions_card_type_code",
        "emoney_transactions",
        ["card_type_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_emoney_transactions_card_type_code", table_name="emoney_transactions")
    op.drop_column("emoney_transactions", "card_type_code")
    op.drop_column("emoney_transactions", "settlement_payload_hex")
