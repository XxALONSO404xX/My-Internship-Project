"""add_notification_system

Revision ID: ca8f76c1acb0
Revises: 97fc445a5e88
Create Date: 2025-05-27 00:45:54.033335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca8f76c1acb0'
down_revision: Union[str, None] = '97fc445a5e88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with notification system."""
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('notification_type', sa.String(50), index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(50), index=True),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('target_type', sa.String(50), nullable=True, index=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('target_name', sa.String(255), nullable=True),
        sa.Column('recipients', sa.JSON()),  # No default as handled by app
        sa.Column('channels', sa.JSON()),    # No default as handled by app
        sa.Column('priority', sa.Integer(), default=3, index=True),
        sa.Column('status', sa.String(50), default='pending', index=True),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('delivery_attempts', sa.Integer(), default=0),
        sa.Column('last_attempt', sa.DateTime(), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False, index=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('notification_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for notifications
    op.create_index(
        'idx_notifications_target',
        'notifications',
        ['target_type', 'target_id']
    )
    op.create_index(
        'idx_notifications_created_priority',
        'notifications',
        ['created_at', 'priority']
    )
    
    # Create notification recipients junction table
    op.create_table(
        'notification_recipients',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('notification_id', sa.Integer(), sa.ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('client_id', sa.String(50), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('is_delivered', sa.Boolean(), default=False),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('delivery_channel', sa.String(50), nullable=True),  # email, sms, push, in-app, etc.
        sa.Column('delivery_status', sa.String(50), default='pending'),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for notification_recipients
    op.create_index(
        'idx_notification_recipients_notification',
        'notification_recipients',
        ['notification_id']
    )
    op.create_index(
        'idx_notification_recipients_client',
        'notification_recipients',
        ['client_id']
    )
    op.create_index(
        'idx_notification_recipient_status',
        'notification_recipients',
        ['is_delivered', 'is_read']
    )


def downgrade() -> None:
    """Downgrade schema by removing notification system tables."""
    # Drop tables in the correct order to respect foreign key constraints
    op.drop_table('notification_recipients')
    op.drop_table('notifications')
