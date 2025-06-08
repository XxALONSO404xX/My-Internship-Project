"""
Add created_by to scans table

Revision ID: abcdef123456
Revises: 1234567890ab
Create Date: 2025-06-05 01:35:30.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'abcdef123456'
down_revision = '1234567890ab'
branch_labels = None
depends_on = None


def upgrade():
    # add created_by column
    op.add_column('scans', sa.Column('created_by', sa.String(length=50), nullable=True))


def downgrade():
    # drop created_by column
    op.drop_column('scans', 'created_by')
