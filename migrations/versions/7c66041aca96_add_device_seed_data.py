"""add_device_seed_data

Revision ID: 7c66041aca96
Revises: c6510e9b500e
Create Date: 2025-05-27 01:10:48.925256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c66041aca96'
down_revision: Union[str, None] = 'c6510e9b500e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
