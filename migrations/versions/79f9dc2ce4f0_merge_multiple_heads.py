"""Merge multiple heads

Revision ID: 79f9dc2ce4f0
Revises: 7c66041aca96, d8a6f2e9c123
Create Date: 2025-05-27 06:19:29.429358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79f9dc2ce4f0'
down_revision: Union[str, None] = ('7c66041aca96', 'd8a6f2e9c123')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
