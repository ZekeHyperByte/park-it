"""drop member_groups table and FK from members

Revision ID: g1h2i3j4k5l6
Revises: f7a2b8c9d0e1
Create Date: 2026-05-30

"""
from alembic import op
import sqlalchemy as sa

revision = 'g1h2i3j4k5l6'
down_revision = 'f7a2b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('members') as batch_op:
        batch_op.drop_constraint('members_member_group_id_fkey', type_='foreignkey')
        batch_op.drop_column('member_group_id')

    op.drop_table('member_groups')


def downgrade() -> None:
    op.create_table(
        'member_groups',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    with op.batch_alter_table('members') as batch_op:
        batch_op.add_column(sa.Column('member_group_id', sa.BigInteger(), nullable=True))
        batch_op.create_foreign_key(
            'members_member_group_id_fkey',
            'member_groups',
            ['member_group_id'],
            ['id'],
        )
