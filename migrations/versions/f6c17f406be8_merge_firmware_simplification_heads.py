"""merge firmware simplification heads

Revision ID: f6c17f406be8
Revises: simplify_firmware_model, simplify_firmware_model_fixed
Create Date: 2025-05-30 16:25:08.986244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6c17f406be8'
down_revision: Union[str, None] = ('simplify_firmware_model', 'simplify_firmware_model_fixed')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
