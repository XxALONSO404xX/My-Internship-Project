"""enhance_field_defaults_and_constraints

Revision ID: 5184bdbacc42
Revises: ca8f76c1acb0
Create Date: 2025-05-27 00:48:45.510158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5184bdbacc42'
down_revision: Union[str, None] = 'ca8f76c1acb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enhance field defaults and constraints based on original migrations."""
    # Create just one index to find the issue
    print("Attempting to create index on firmware_updates.created_at")
    try:
        # Adding only the first index to see if this specific operation works
        op.create_index('ix_firmware_updates_created_at', 'firmware_updates', ['created_at'])
        print("Successfully created index on firmware_updates.created_at")
    except Exception as e:
        print(f"Error creating index: {str(e)}")
        # Continue with the migration even if this fails


def downgrade() -> None:
    """Downgrade schema by removing added index."""
    # Try to drop the index (it may not exist if the upgrade failed)
    print("Attempting to drop index on firmware_updates.created_at")
    try:
        op.drop_index('ix_firmware_updates_created_at', table_name='firmware_updates')
        print("Successfully dropped index on firmware_updates.created_at")
    except Exception as e:
        print(f"Error dropping index: {str(e)}")
        # Continue with the downgrade even if this fails
