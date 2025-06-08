"""
Revision ID: f999_activity_target_id_varchar
Revises: fedcba987654
Create Date: 2025-06-08 04:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f999_activity_target_id_varchar'
down_revision = 'fedcba987654'
branch_labels = None
depends_on = None


def upgrade():
    # Change activities.target_id from Integer to String(64)
    op.alter_column(
        'activities',
        'target_id',
        existing_type=sa.Integer(),
        type_=sa.String(length=64),
        postgresql_using='target_id::varchar'
    )

def downgrade():
    # Revert activities.target_id back to Integer
    op.alter_column(
        'activities',
        'target_id',
        existing_type=sa.String(length=64),
        type_=sa.Integer(),
        postgresql_using='target_id::integer'
    )
