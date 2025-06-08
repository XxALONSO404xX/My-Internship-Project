"""
Revision ID: fedcba987654
Revises: 445566778899, f405_fix_notification_target_id
Create Date: 2025-06-08 04:12:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fedcba987654'
down_revision = ('445566778899', 'f405_fix_notification_target_id')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # merge heads to unify migration history
    pass


def downgrade() -> None:
    # no-op merge downgrade
    pass
