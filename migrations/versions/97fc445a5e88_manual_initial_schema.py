"""manual_initial_schema

Revision ID: 97fc445a5e88
Revises: 7cd56dff1b68
Create Date: 2025-05-26 23:10:11.165592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97fc445a5e88'
down_revision: Union[str, None] = None  # Starting fresh with no previous migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create clients table first (this is the table other tables depend on)
    op.create_table('clients',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('username', sa.String(100), unique=True),
        sa.Column('email', sa.String(100), unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verification_date', sa.DateTime(), nullable=True),
        sa.Column('preferences', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True)
    )
    op.create_index(op.f('ix_clients_email'), 'clients', ['email'], unique=True)
    op.create_index(op.f('ix_clients_id'), 'clients', ['id'], unique=False)
    op.create_index(op.f('ix_clients_username'), 'clients', ['username'], unique=True)
    
    # Then create all other tables that don't depend on clients
    op.create_table('activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_ip', sa.String(length=50), nullable=True),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('target_name', sa.String(length=255), nullable=True),
        sa.Column('previous_state', sa.JSON(), nullable=True),
        sa.Column('new_state', sa.JSON(), nullable=True),
        sa.Column('activity_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_activities_action'), 'activities', ['action'], unique=False)
    op.create_index(op.f('ix_activities_activity_type'), 'activities', ['activity_type'], unique=False)
    op.create_index(op.f('ix_activities_id'), 'activities', ['id'], unique=False)
    op.create_index(op.f('ix_activities_target_id'), 'activities', ['target_id'], unique=False)
    op.create_index(op.f('ix_activities_target_type'), 'activities', ['target_type'], unique=False)
    op.create_index(op.f('ix_activities_timestamp'), 'activities', ['timestamp'], unique=False)
    op.create_index(op.f('ix_activities_user_id'), 'activities', ['user_id'], unique=False)
    
    op.create_table('groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_type', sa.String(length=50), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_group_type'), 'groups', ['group_type'], unique=False)
    op.create_index(op.f('ix_groups_id'), 'groups', ['id'], unique=False)
    op.create_index(op.f('ix_groups_name'), 'groups', ['name'], unique=False)
    
    op.create_table('rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=True),
        sa.Column('schedule', sa.String(length=100), nullable=True),
        sa.Column('target_device_ids', sa.JSON(), nullable=True, comment='List of specific device IDs this rule applies to'),
        sa.Column('conditions', sa.JSON(), nullable=False),
        sa.Column('actions', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('last_triggered', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rules_id'), 'rules', ['id'], unique=False)
    op.create_index(op.f('ix_rules_name'), 'rules', ['name'], unique=False)
    op.create_index(op.f('ix_rules_rule_type'), 'rules', ['rule_type'], unique=False)
    
    # Then create firmware which depends on clients
    op.create_table('firmware',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('device_type', sa.String(length=100), nullable=False),
        sa.Column('release_date', sa.DateTime(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('download_url', sa.String(length=255), nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('is_critical', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_firmware_device_type'), 'firmware', ['device_type'], unique=False)
    
    # Create devices table
    op.create_table('devices',
        sa.Column('hash_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('mac_address', sa.String(length=50), nullable=True),
        sa.Column('device_type', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('firmware_version', sa.String(length=100), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('is_online', sa.Boolean(), nullable=True),
        sa.Column('ports', sa.JSON(), nullable=True),
        sa.Column('supports_http', sa.Boolean(), nullable=True),
        sa.Column('supports_mqtt', sa.Boolean(), nullable=True),
        sa.Column('supports_coap', sa.Boolean(), nullable=True),
        sa.Column('supports_websocket', sa.Boolean(), nullable=True),
        sa.Column('supports_tls', sa.Boolean(), nullable=True),
        sa.Column('tls_version', sa.String(length=20), nullable=True),
        sa.Column('cert_expiry', sa.DateTime(), nullable=True),
        sa.Column('cert_issued_by', sa.String(length=255), nullable=True),
        sa.Column('cert_strength', sa.Integer(), nullable=True),
        sa.Column('discovery_method', sa.String(length=50), nullable=True),
        sa.Column('discovery_info', sa.JSON(), nullable=True),
        sa.Column('auth_type', sa.String(length=50), nullable=True),
        sa.Column('auth_data', sa.JSON(), nullable=True),
        sa.Column('device_metadata', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('firmware_update_support', sa.Boolean(), nullable=True),
        sa.Column('current_firmware_id', sa.String(length=36), nullable=True),
        sa.Column('last_firmware_check', sa.DateTime(), nullable=True),
        sa.Column('firmware_auto_update', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['current_firmware_id'], ['firmware.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('hash_id')
    )
    op.create_index(op.f('ix_devices_hash_id'), 'devices', ['hash_id'], unique=False)
    op.create_index(op.f('ix_devices_ip_address'), 'devices', ['ip_address'], unique=False)
    op.create_index(op.f('ix_devices_mac_address'), 'devices', ['mac_address'], unique=True)
    op.create_index(op.f('ix_devices_name'), 'devices', ['name'], unique=False)
    
    # Create firmware_batch_updates that depends on firmware and clients
    op.create_table('firmware_batch_updates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('firmware_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_devices', sa.Integer(), nullable=True),
        sa.Column('successful_devices', sa.Integer(), nullable=True),
        sa.Column('failed_devices', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['firmware_id'], ['firmware.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create device_groups that depends on devices and groups
    op.create_table('device_groups',
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.hash_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('device_id', 'group_id')
    )
    
    # Create firmware_updates that depends on devices, firmware, and firmware_batch_updates
    op.create_table('firmware_updates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('firmware_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('speed_kbps', sa.Integer(), nullable=True),
        sa.Column('estimated_time_remaining', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('batch_id', sa.String(length=36), nullable=True),
        sa.Column('secure_channel', sa.Boolean(), nullable=True),
        sa.Column('encryption_method', sa.String(length=50), nullable=True),
        sa.Column('signature_verified', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['firmware_batch_updates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.hash_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['firmware_id'], ['firmware.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_firmware_updates_device_id'), 'firmware_updates', ['device_id'], unique=False)
    op.create_index(op.f('ix_firmware_updates_status'), 'firmware_updates', ['status'], unique=False)
    
    # Create device_firmware_history table
    op.create_table('device_firmware_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('firmware_id', sa.String(length=36), nullable=False),
        sa.Column('previous_version', sa.String(length=50), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('update_method', sa.String(length=50), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.hash_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['firmware_id'], ['firmware.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create sensor_readings that depends on devices
    op.create_table('sensor_readings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('sensor_type', sa.String(length=50), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('reading_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.hash_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sensor_readings_device_id'), 'sensor_readings', ['device_id'], unique=False)
    op.create_index(op.f('ix_sensor_readings_id'), 'sensor_readings', ['id'], unique=False)
    op.create_index(op.f('ix_sensor_readings_sensor_type'), 'sensor_readings', ['sensor_type'], unique=False)
    op.create_index(op.f('ix_sensor_readings_timestamp'), 'sensor_readings', ['timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in the reverse order they were created
    op.drop_table('sensor_readings')
    op.drop_table('device_firmware_history')
    op.drop_table('firmware_updates')
    op.drop_table('device_groups')
    op.drop_table('firmware_batch_updates')
    op.drop_table('devices')
    op.drop_table('firmware')
    op.drop_table('rules')
    op.drop_table('groups')
    op.drop_table('activities')
    op.drop_table('clients')
