"""add_protocol_and_printer_config

Revision ID: b7b386fcd5bc
Revises: 1d087dbbd036
Create Date: 2026-04-25 20:29:15.607499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7b386fcd5bc'
down_revision: Union[str, None] = '1d087dbbd036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add printer_ip_address and printer_device to gate_ins
    op.add_column('gate_ins', sa.Column('printer_ip_address', sa.String(length=100), nullable=True))
    op.add_column('gate_ins', sa.Column('printer_device', sa.String(length=100), nullable=True))

    # Add printer_ip_address and printer_device to gate_outs
    op.add_column('gate_outs', sa.Column('printer_ip_address', sa.String(length=100), nullable=True))
    op.add_column('gate_outs', sa.Column('printer_device', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('gate_outs', 'printer_device')
    op.drop_column('gate_outs', 'printer_ip_address')
    op.drop_column('gate_ins', 'printer_device')
    op.drop_column('gate_ins', 'printer_ip_address')
