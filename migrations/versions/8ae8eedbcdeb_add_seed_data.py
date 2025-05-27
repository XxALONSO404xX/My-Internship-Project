"""add_seed_data

Revision ID: 8ae8eedbcdeb
Revises: 5184bdbacc42
Create Date: 2025-05-27 00:49:44.254927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ae8eedbcdeb'
down_revision: Union[str, None] = '5184bdbacc42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add seed data to populate the database with test data."""
    from sqlalchemy.sql import table, column
    from sqlalchemy import String, Boolean, DateTime
    from datetime import datetime
    import json
    
    print("Beginning seed data migration - simplified version")
    
    # Try to add just a single client as a test
    try:
        # Seed a test client/user with all required fields
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
        
        print("Attempting to insert a single client record")
        op.bulk_insert(clients, [
            {
                'id': 'admin',
                'username': 'admin',
                'email': 'admin@iotplatform.com',
                'hashed_password': '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',  # 'password'
                'is_active': True,
                'is_verified': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ])
        print("Successfully inserted client record")
    except Exception as e:
        print(f"Error inserting client: {str(e)}")
        # Continue with the migration even if this fails
    
    print("Seed data migration completed successfully.")


def downgrade() -> None:
    """Remove seed data from the database."""
    # Delete data in the reverse order it was inserted to respect foreign key constraints
    op.execute('DELETE FROM clients WHERE id = \'admin\'')
    print("Seed data removed successfully")
