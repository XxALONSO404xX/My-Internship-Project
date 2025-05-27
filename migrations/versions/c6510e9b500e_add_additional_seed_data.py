"""add_additional_seed_data

Revision ID: c6510e9b500e
Revises: 8ae8eedbcdeb
Create Date: 2025-05-27 01:08:51.019036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6510e9b500e'
down_revision: Union[str, None] = '8ae8eedbcdeb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add additional seed data for testing."""
    from sqlalchemy.sql import table, column
    from sqlalchemy import String, Integer, Boolean, DateTime, JSON, Text
    from datetime import datetime
    import json
    
    print("Beginning additional seed data migration")
    
    # Add test user
    try:
        clients = table('clients',
            column('id', String),
            column('username', String),
            column('email', String),
            column('hashed_password', String),
            column('is_active', Boolean),
            column('is_verified', Boolean),
            column('created_at', DateTime),
            column('updated_at', DateTime)
        )
        
        print("Adding test user")
        op.bulk_insert(clients, [
            {
                'id': 'test_user',
                'username': 'test_user',
                'email': 'test@iotplatform.com',
                'hashed_password': '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',  # 'password'
                'is_active': True,
                'is_verified': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ])
        print("Successfully added test user")
    except Exception as e:
        print(f"Error inserting test user: {str(e)}")
    
    # Add test group
    try:
        groups = table('groups',
            column('id', Integer),
            column('name', String),
            column('description', Text),
            column('group_type', String),
            column('attributes', JSON),
            column('icon', String),
            column('color', String),
            column('is_active', Boolean),
            column('created_at', DateTime),
            column('updated_at', DateTime)
        )
        
        print("Adding test group")
        op.bulk_insert(groups, [
            {
                'id': 1,
                'name': 'Test Group',
                'description': 'Group for testing purposes',
                'group_type': 'test',
                'attributes': json.dumps({'test_key': 'test_value'}),
                'icon': 'test-icon',
                'color': '#42f5a7',
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ])
        print("Successfully added test group")
    except Exception as e:
        print(f"Error inserting test group: {str(e)}")
    
    # Add test firmware
    try:
        firmware = table('firmware',
            column('id', String),
            column('version', String),
            column('name', String),
            column('description', Text),
            column('file_path', String),
            column('file_size', Integer),
            column('file_hash', String),
            column('release_notes', Text),
            column('is_active', Boolean),
            column('release_date', DateTime),
            column('created_at', DateTime),
            column('updated_at', DateTime)
        )
        
        # Generate unique IDs for firmware versions
        import hashlib
        import uuid
        
        firmware_id_1 = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]
        firmware_id_2 = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]
        
        print("Adding test firmware")
        op.bulk_insert(firmware, [
            {
                'id': firmware_id_1,
                'version': 'v1.0.0',
                'name': 'Test Device Firmware',
                'description': 'Initial firmware for test devices',
                'file_path': '/firmware/test_device_v1.0.0.bin',
                'file_size': 102400,  # 100kb
                'file_hash': hashlib.sha256('test_device_firmware_v1'.encode()).hexdigest(),
                'release_notes': 'Initial release for testing purposes.',
                'is_active': True,
                'release_date': datetime.utcnow() - timedelta(days=30),
                'created_at': datetime.utcnow() - timedelta(days=30),
                'updated_at': datetime.utcnow() - timedelta(days=30)
            },
            {
                'id': firmware_id_2,
                'version': 'v1.1.0',
                'name': 'Test Device Firmware',
                'description': 'Updated firmware for test devices',
                'file_path': '/firmware/test_device_v1.1.0.bin',
                'file_size': 153600,  # 150kb
                'file_hash': hashlib.sha256('test_device_firmware_v1.1'.encode()).hexdigest(),
                'release_notes': 'Improved performance and stability.',
                'is_active': True,
                'release_date': datetime.utcnow() - timedelta(days=7),
                'created_at': datetime.utcnow() - timedelta(days=7),
                'updated_at': datetime.utcnow() - timedelta(days=7)
            }
        ])
        print("Successfully added test firmware")
    except Exception as e:
        print(f"Error inserting firmware: {str(e)}")
    
    # Add test devices
    try:
        from datetime import timedelta
        
        devices = table('devices',
            column('hash_id', String),
            column('name', String),
            column('ip_address', String),
            column('mac_address', String),
            column('model', String),
            column('manufacturer', String),
            column('firmware_version', String),
            column('status', String),
            column('last_seen', DateTime),
            column('location', String),
            column('notes', Text),
            column('attributes', JSON),
            column('tls_enabled', Boolean),
            column('certificate_expiry', DateTime),
            column('created_at', DateTime),
            column('updated_at', DateTime),
            column('current_firmware_id', String)
        )
        
        # Generate unique IDs for devices
        device1_hash_id = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]
        device2_hash_id = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]
        device3_hash_id = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]
        
        print("Adding test devices")
        op.bulk_insert(devices, [
            {
                'hash_id': device1_hash_id,
                'name': 'Test Device 1',
                'ip_address': '192.168.1.101',
                'mac_address': '00:1B:44:11:3A:B7',
                'model': 'TestDevice2000',
                'manufacturer': 'IoT Test Inc.',
                'firmware_version': 'v1.1.0',
                'status': 'online',
                'last_seen': datetime.utcnow(),
                'location': 'Test Location 1',
                'notes': 'This is a test device for demonstration purposes',
                'attributes': json.dumps({'test_attribute': 'value1', 'reporting_interval': 300}),
                'tls_enabled': True,
                'certificate_expiry': datetime.utcnow() + timedelta(days=365),
                'created_at': datetime.utcnow() - timedelta(days=45),
                'updated_at': datetime.utcnow(),
                'current_firmware_id': firmware_id_2
            },
            {
                'hash_id': device2_hash_id,
                'name': 'Test Device 2',
                'ip_address': '192.168.1.102',
                'mac_address': '00:1B:44:11:3A:C8',
                'model': 'TestDevice2000',
                'manufacturer': 'IoT Test Inc.',
                'firmware_version': 'v1.0.0',
                'status': 'online',
                'last_seen': datetime.utcnow() - timedelta(hours=2),
                'location': 'Test Location 2',
                'notes': 'This is another test device',
                'attributes': json.dumps({'test_attribute': 'value2', 'reporting_interval': 600}),
                'tls_enabled': True,
                'certificate_expiry': datetime.utcnow() + timedelta(days=365),
                'created_at': datetime.utcnow() - timedelta(days=45),
                'updated_at': datetime.utcnow() - timedelta(hours=2),
                'current_firmware_id': firmware_id_1
            },
            {
                'hash_id': device3_hash_id,
                'name': 'Test Device 3',
                'ip_address': '192.168.1.103',
                'mac_address': '00:1B:44:11:3A:D9',
                'model': 'TestDevice3000',
                'manufacturer': 'IoT Test Inc.',
                'firmware_version': 'v1.0.0',
                'status': 'offline',
                'last_seen': datetime.utcnow() - timedelta(days=2),
                'location': 'Test Location 3',
                'notes': 'This device is currently offline',
                'attributes': json.dumps({'test_attribute': 'value3', 'reporting_interval': 900}),
                'tls_enabled': False,
                'certificate_expiry': None,
                'created_at': datetime.utcnow() - timedelta(days=30),
                'updated_at': datetime.utcnow() - timedelta(days=2),
                'current_firmware_id': firmware_id_1
            }
        ])
        print("Successfully added test devices")
    except Exception as e:
        print(f"Error inserting devices: {str(e)}")
    
    # Add device-group associations
    try:
        device_groups = table('device_groups',
            column('device_id', String),
            column('group_id', Integer)
        )
        
        print("Adding device-group associations")
        op.bulk_insert(device_groups, [
            {
                'device_id': device1_hash_id,
                'group_id': 1  # The 'Test Group' we created earlier
            },
            {
                'device_id': device2_hash_id,
                'group_id': 1  # The 'Test Group' we created earlier
            }
        ])
        print("Successfully added device-group associations")
    except Exception as e:
        print(f"Error inserting device_groups: {str(e)}")
    
    # Add firmware updates
    try:
        firmware_updates = table('firmware_updates',
            column('id', String),
            column('device_id', String),
            column('firmware_id', String),
            column('status', String),
            column('started_at', DateTime),
            column('completed_at', DateTime),
            column('notes', Text),
            column('created_at', DateTime),
            column('secure_channel', Boolean),
            column('encryption_method', String),
            column('signature_verified', Boolean)
        )
        
        print("Adding firmware update records")
        op.bulk_insert(firmware_updates, [
            {
                'id': hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32],
                'device_id': device1_hash_id,
                'firmware_id': firmware_id_1,
                'status': 'completed',
                'started_at': datetime.utcnow() - timedelta(days=20),
                'completed_at': datetime.utcnow() - timedelta(days=20),
                'notes': 'Initial firmware installation',
                'created_at': datetime.utcnow() - timedelta(days=20),
                'secure_channel': True,
                'encryption_method': 'AES-256',
                'signature_verified': True
            },
            {
                'id': hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32],
                'device_id': device1_hash_id,
                'firmware_id': firmware_id_2,
                'status': 'completed',
                'started_at': datetime.utcnow() - timedelta(days=5),
                'completed_at': datetime.utcnow() - timedelta(days=5),
                'notes': 'Upgrade to latest version',
                'created_at': datetime.utcnow() - timedelta(days=5),
                'secure_channel': True,
                'encryption_method': 'AES-256',
                'signature_verified': True
            },
            {
                'id': hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32],
                'device_id': device2_hash_id,
                'firmware_id': firmware_id_2,
                'status': 'scheduled',
                'started_at': None,
                'completed_at': None,
                'notes': 'Scheduled upgrade to latest version',
                'created_at': datetime.utcnow() - timedelta(days=1),
                'secure_channel': True,
                'encryption_method': 'AES-256',
                'signature_verified': None
            }
        ])
        print("Successfully added firmware update records")
    except Exception as e:
        print(f"Error inserting firmware_updates: {str(e)}")
        
    print("Additional seed data migration completed successfully")


def downgrade() -> None:
    """Remove the additional seed data."""
    print("Removing additional seed data in reverse order")
    
    # Delete in reverse order to respect foreign key constraints
    try:
        print("Removing firmware updates")
        op.execute("DELETE FROM firmware_updates WHERE device_id IN (SELECT hash_id FROM devices WHERE name LIKE 'Test Device%')")
        print("Successfully removed firmware updates")
    except Exception as e:
        print(f"Error removing firmware updates: {str(e)}")
    
    try:
        print("Removing device-group associations")
        op.execute("DELETE FROM device_groups WHERE device_id IN (SELECT hash_id FROM devices WHERE name LIKE 'Test Device%')")
        print("Successfully removed device-group associations")
    except Exception as e:
        print(f"Error removing device-group associations: {str(e)}")
    
    try:
        print("Removing test devices")
        op.execute("DELETE FROM devices WHERE name LIKE 'Test Device%'")
        print("Successfully removed test devices")
    except Exception as e:
        print(f"Error removing test devices: {str(e)}")
    
    try:
        print("Removing test firmware")
        op.execute("DELETE FROM firmware WHERE name = 'Test Device Firmware'")
        print("Successfully removed test firmware")
    except Exception as e:
        print(f"Error removing test firmware: {str(e)}")
    
    try:
        print("Removing test group")
        op.execute("DELETE FROM groups WHERE name = 'Test Group'")
        print("Successfully removed test group")
    except Exception as e:
        print(f"Error removing test group: {str(e)}")
    
    try:
        print("Removing test user")
        op.execute("DELETE FROM clients WHERE id = 'test_user'")
        print("Successfully removed test user")
    except Exception as e:
        print(f"Error removing test user: {str(e)}")
    
    print("Additional seed data removal completed successfully")
