"""Add tokens table

Revision ID: d8a6f2e9c123
Revises: ca8f76c1acb0
Create Date: 2025-05-27 02:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a6f2e9c123'
down_revision: Union[str, None] = 'ca8f76c1acb0'  # Set to the most recent migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tokens table for authentication and password reset."""
    op.create_table('tokens',
        sa.Column('token', sa.String(120), primary_key=True),
        sa.Column('client_id', sa.String(50), sa.ForeignKey('clients.id', ondelete='CASCADE')),
        sa.Column('token_type', sa.String(20)),  # "verification" or "reset"
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('token_metadata', sa.Text(), nullable=True)  # For storing additional data as JSON
    )
    op.create_index(op.f('ix_tokens_token'), 'tokens', ['token'], unique=True)
    op.create_index(op.f('ix_tokens_client_id'), 'tokens', ['client_id'], unique=False)
    op.create_index(op.f('ix_tokens_token_type'), 'tokens', ['token_type'], unique=False)


def downgrade() -> None:
    """Drop tokens table."""
    op.drop_index(op.f('ix_tokens_token_type'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_client_id'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_token'), table_name='tokens')
    op.drop_table('tokens')
