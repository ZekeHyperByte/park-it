"""add default_gate_id to pos table

Revision ID: f7a2b8c9d0e1
Revises: 2026_04_27_unified_gate_and_pos
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a2b8c9d0e1'
down_revision: Union[str, None] = '2026_04_27_unified_gate_and_pos'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pos', sa.Column('default_gate_id', sa.BigInteger(), sa.ForeignKey('gates.id'), nullable=True))
    op.create_index('ix_pos_default_gate_id', 'pos', ['default_gate_id'])


def downgrade() -> None:
    op.drop_index('ix_pos_default_gate_id', table_name='pos')
    op.drop_column('pos', 'default_gate_id')
