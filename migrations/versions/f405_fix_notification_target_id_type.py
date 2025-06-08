"""
Revision ID: f405_fix_notification_target_id
Revises: ca8f76c1acb0
Create Date: 2025-06-08 04:11:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f405_fix_notification_target_id'
down_revision = 'ca8f76c1acb0'
branch_labels = None
depends_on = None


def upgrade():
    # Change notifications.target_id from Integer to String(64)
    op.alter_column(
        'notifications',
        'target_id',
        existing_type=sa.Integer(),
        type_=sa.String(length=64),
        postgresql_using='target_id::varchar'
    )


def downgrade():
    # Revert notifications.target_id back to Integer
    op.alter_column(
        'notifications',
        'target_id',
        existing_type=sa.String(length=64),
        type_=sa.Integer(),
        postgresql_using='target_id::integer'
    )
