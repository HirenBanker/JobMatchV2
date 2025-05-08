import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
# DB_HOST = os.getenv("DB_HOST", "localhost")
# DB_PORT = os.getenv("DB_PORT", "5432")
# DB_USER = os.getenv("DB_USER", "postgres")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
# DB_NAME = os.getenv("DB_NAME", "jobmatch")

def test_connection():
    """Test database connection and check admin user"""
    try:
        # Connect to the database
        # print(f"Connecting to database: {DB_NAME} on {DB_HOST}:{DB_PORT} as {DB_USER}")
        # conn = psycopg2.connect(
        #     host=DB_HOST,
        #     port=DB_PORT,
        #     user=DB_USER,
        #     password=DB_PASSWORD,
        #     database=DB_NAME
        # )
        
        # Connect to the database using DATABASE_URL
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("Error: DATABASE_URL environment variable not set.")
            return False

        print(f"Attempting to connect using DATABASE_URL...")
        conn = psycopg2.connect(database_url)
        print("Database connection successful!")
        
        cursor = conn.cursor()
        
        # Check if admin user exists
        cursor.execute("SELECT id, username, email, user_type FROM users WHERE user_type = 'admin'")
        admin_users = cursor.fetchall()
        
        if admin_users:
            print("\nAdmin users found:")
            for user in admin_users:
                print(f"ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Type: {user[3]}")
        else:
            print("\nNo admin users found.")
        
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    test_connection()