"""Add connection_type and relay_mode

Revision ID: 1d087dbbd036
Revises: 914e5fe1c754
Create Date: 2026-04-25 15:38:19.613597

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1d087dbbd036'
down_revision: str | None = '914e5fe1c754'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns as nullable first (to handle existing data)
    op.add_column('emoney_readers', sa.Column('connection_type', sa.String(length=30), nullable=True))
    op.add_column('gate_ins', sa.Column('relay_mode', sa.String(length=20), nullable=True))
    op.add_column('gate_outs', sa.Column('relay_mode', sa.String(length=20), nullable=True))

    # Set default values for existing rows
    op.execute("UPDATE emoney_readers SET connection_type = 'CONTROLLER_PASSTHROUGH'")
    op.execute("UPDATE gate_ins SET relay_mode = 'SINGLE'")
    op.execute("UPDATE gate_outs SET relay_mode = 'SINGLE'")

    # Make columns non-nullable
    op.alter_column('emoney_readers', 'connection_type', nullable=False)
    op.alter_column('gate_ins', 'relay_mode', nullable=False)
    op.alter_column('gate_outs', 'relay_mode', nullable=False)


def downgrade() -> None:
    op.drop_column('gate_outs', 'relay_mode')
    op.drop_column('gate_ins', 'relay_mode')
    op.drop_column('emoney_readers', 'connection_type')
