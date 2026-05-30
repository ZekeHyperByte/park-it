"""merge_multiple_heads

Revision ID: e1f655046e3b
Revises: g1h2i3j4k5l6, h1i2j3k4l5m6
Create Date: 2026-05-31 00:58:24.198979

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f655046e3b'
down_revision: Union[str, None] = ('g1h2i3j4k5l6', 'h1i2j3k4l5m6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
