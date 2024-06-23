import psycopg2
from psycopg2 import sql

# Define your database connection parameters
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "payments_project"
DB_USER = "zachmandell"
DB_PASSWORD = ""

def test_connection():
    try:
        # Establish the connection
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        # Create a cursor object
        cursor = connection.cursor()

        # Execute a simple SQL query to test the connection
        cursor.execute("SELECT version();")

        # Fetch the result
        db_version = cursor.fetchone()
        print("Database version:", db_version)

        # Close the cursor and connection
        cursor.close()
        connection.close()
        
    except Exception as error:
        print(f"Error connecting to the database: {error}")

if __name__ == "__main__":
    test_connection()