"""
Reset the alembic_version table in the database
"""
import psycopg2
from config.settings import settings

def reset_alembic_version():
    """Drop the alembic_version table to completely reset migration tracking"""
    print("Resetting alembic_version table...")
    
    try:
        # Connection parameters
        conn_params = {
            'dbname': settings.POSTGRES_DB,
            'user': settings.POSTGRES_USER,
            'password': settings.POSTGRES_PASSWORD,
            'host': settings.POSTGRES_SERVER,
            'port': settings.POSTGRES_PORT
        }
        
        # Connect to the database
        print(f"Connecting to {settings.POSTGRES_DB} database...")
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Drop the alembic_version table
        cursor.execute("DROP TABLE IF EXISTS alembic_version")
        print("Dropped alembic_version table")
        
        cursor.close()
        conn.close()
        print("Database connection closed")
        return True
        
    except Exception as e:
        print(f"Error resetting alembic_version: {e}")
        return False

if __name__ == "__main__":
    print("Alembic Version Reset Utility")
    print("============================")
    success = reset_alembic_version()
    
    if success:
        print("\nAlembic version table has been reset successfully.")
        print("You can now create a new migration with 'alembic revision --autogenerate'.")
    else:
        print("\nFailed to reset alembic version table. Check the error messages above.")
