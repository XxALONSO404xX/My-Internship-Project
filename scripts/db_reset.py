"""
Database reset script for IoT Platform

This script:
1. Drops existing tables directly using SQL
2. Recreates the public schema
3. Runs migrations to rebuild the database
"""
import asyncio
import subprocess
import sys
import os
import psycopg2
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.sql import text

from app.models.database import async_engine
from config.settings import settings

def drop_all_tables_direct_sql():
    """Drop all tables directly using psycopg2 - more reliable than SQLAlchemy for this task"""
    try:
        # Extract connection parameters from settings
        conn_params = {
            'dbname': settings.POSTGRES_DB,
            'user': settings.POSTGRES_USER,
            'password': settings.POSTGRES_PASSWORD,
            'host': settings.POSTGRES_SERVER,
            'port': settings.POSTGRES_PORT
        }
        
        # Connect directly with psycopg2
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected to PostgreSQL database. Dropping all tables...")
        
        # Disable triggers temporarily
        cursor.execute("SET session_replication_role = 'replica';")
        
        # Get all tables in the public schema
        cursor.execute("""
        SELECT tablename FROM pg_tables WHERE schemaname = 'public'
        """)
        
        tables = cursor.fetchall()
        
        if tables:
            # Create a DROP TABLE statement for all tables with CASCADE
            drop_query = "DROP TABLE IF EXISTS " + ", ".join(f'"{table[0]}"' for table in tables) + " CASCADE;"
            print(f"Dropping {len(tables)} tables...")
            
            # Execute the drop
            cursor.execute(drop_query)
            print("All tables dropped successfully")
        else:
            print("No tables found in public schema")
            
        # Re-enable triggers
        cursor.execute("SET session_replication_role = 'origin';")
        
        # Drop alembic_version table separately (if it exists)
        cursor.execute("DROP TABLE IF EXISTS alembic_version CASCADE;")
        
        cursor.close()
        conn.close()
        print("Database connection closed")
        return True
        
    except Exception as e:
        print(f"Error dropping tables: {str(e)}")
        
        return False

async def reset_database():
    """Reset the database completely"""
    print("Starting database reset process...")
    
    # First, drop all tables directly with SQL (more reliable)
    success = drop_all_tables_direct_sql()
    if not success:
        print("Failed to drop tables. Aborting.")
        return False

    # Use the async engine from database module
    engine = async_engine
    
    async with engine.begin() as conn:
        # Recreate public schema to be safe
        print("\nRecreating public schema...")
        await conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
        await conn.execute(text('CREATE SCHEMA public'))
        
        # Set default permissions
        print("Setting schema permissions...")
        await conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
        await conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
        
        # Make public schema the default
        print("Setting public as default schema...")
        await conn.execute(text('ALTER DATABASE "ProjectBD" SET search_path TO public'))
    
    print("Schema reset complete!")
    
    # Run Alembic migrations
    print("\nRunning database migrations...")
    try:
        # Check if we have the new comprehensive migration
        migration_files = os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations", "versions"))
        
        if not migration_files:
            print("No migration files found. You need to create a migration first.")
            print("Run: alembic revision --autogenerate -m \"complete_schema_with_firmware\"")
            return False
        
        # Run the migrations to the latest version
        print("Running migrations to the latest version...")
        subprocess.run(
            ["alembic", "upgrade", "head"], 
            check=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        print("\nMigrations completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        return False
    
    print("\nDatabase reset and migrations completed successfully!")
    print("The IoT Platform database has been recreated with all tables.")
    return True

if __name__ == "__main__":
    print("IoT Platform Database Reset Utility")
    print("===================================")
    
    confirm = input("This will DESTROY ALL DATA in your database and recreate it. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Operation cancelled.")
        sys.exit(0)
    
    asyncio.run(reset_database())
