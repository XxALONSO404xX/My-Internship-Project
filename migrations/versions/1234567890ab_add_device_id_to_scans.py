"""
Add device_id to scans table

Revision ID: 1234567890ab
Revises: f6c17f406be8
Create Date: 2025-06-05 01:25:47.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = 'f6c17f406be8'
branch_labels = None
depends_on = None


def upgrade():
    # add device_id column and FK to devices.hash_id
    op.add_column('scans', sa.Column('device_id', sa.String(length=64), nullable=True))
    op.create_foreign_key('fk_scans_device_id', 'scans', 'devices', ['device_id'], ['hash_id'])


def downgrade():
    # drop FK and column
    op.drop_constraint('fk_scans_device_id', 'scans', type_='foreignkey')
    op.drop_column('scans', 'device_id')
