"""
Check if batch_id in firmware_updates table is nullable and check schema of firmware_batch_updates
"""
import psycopg2

def check_column_nullable(table_name, column_name):
    """Check if a column can be NULL"""
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
        
        # Check if column is nullable
        cur.execute(f"""
        SELECT is_nullable 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' 
        AND column_name = '{column_name}'
        """)
        
        result = cur.fetchone()
        print(f"Column {column_name} in table {table_name} nullable: {result[0]}")
        
        # Close the cursor
        cur.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the connection
        if conn is not None:
            conn.close()

def check_table_schema(table_name):
    """Get the column details for a table"""
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
        
        # Check if table exists
        cur.execute(f"""
        SELECT EXISTS (
           SELECT FROM information_schema.tables 
           WHERE table_name = '{table_name}'
        );
        """)
        
        exists = cur.fetchone()[0]
        
        if exists:
            # Get the column information
            cur.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
            """)
            
            # Fetch the results
            columns = cur.fetchall()
            
            # Print the column information
            print(f"\nColumns for table '{table_name}':")
            for col_name, data_type, is_nullable, default in columns:
                print(f"  {col_name} ({data_type}, nullable: {is_nullable}, default: {default})")
        else:
            print(f"Table '{table_name}' does not exist")
        
        # Close the cursor
        cur.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the connection
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    # Check if batch_id in firmware_updates is nullable
    check_column_nullable("firmware_updates", "batch_id")
    
    # Check schema of firmware_batch_updates
    check_table_schema("firmware_batch_updates")
