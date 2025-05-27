"""
Script to inspect the database schema to see the actual column names
"""
import psycopg2

def get_table_columns(table_name):
    """Get the column names for a specific table"""
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname="ProjectBD",
            user="postgres",
            password="1234",
            host="localhost",
            port="5432"
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Get the column information
        cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
        """)
        
        # Fetch the results
        columns = cur.fetchall()
        
        # Print the column information
        print(f"\nColumns for table '{table_name}':")
        for col_name, data_type in columns:
            print(f"  {col_name} ({data_type})")
        
        # Close the cursor
        cur.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the connection
        if conn is not None:
            conn.close()

def main():
    """Main function to inspect schema"""
    # List of tables to inspect
    tables = ["firmware", "devices", "device_groups", "firmware_updates"]
    
    # Get columns for each table
    for table in tables:
        get_table_columns(table)

if __name__ == "__main__":
    main()
