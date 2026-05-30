"""add auth_type to cameras table

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-05-30

"""
from alembic import op
import sqlalchemy as sa

revision = 'h1i2j3k4l5m6'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'cameras',
        sa.Column('auth_type', sa.String(20), nullable=False, server_default='none'),
    )


def downgrade() -> None:
    op.drop_column('cameras', 'auth_type')
