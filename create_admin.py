import psycopg2
import bcrypt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "jobmatch")

def hash_password(password):
    """Hash a password for storing"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_admin_user(username, email, password):
    """Create a new admin user"""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        cursor = conn.cursor()
        
        # Hash the password
        password_hash = hash_password(password)
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute("""
                UPDATE users 
                SET email = %s, password_hash = %s, user_type = 'admin'
                WHERE username = %s
            """, (email, password_hash, username))
            print(f"Updated existing user '{username}' to admin with new password")
        else:
            # Create new admin user
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, user_type)
                VALUES (%s, %s, %s, 'admin')
            """, (username, email, password_hash))
            print(f"Created new admin user '{username}'")
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Create admin user with known credentials
    admin_username = "admin"
    admin_email = "admin@jobmatch.com"
    admin_password = "admin123"
    
    success = create_admin_user(admin_username, admin_email, admin_password)
    
    if success:
        print(f"\nAdmin user created/updated successfully!")
        print(f"Username: {admin_username}")
        print(f"Password: {admin_password}")
        print("\nYou can now log in with these credentials.")
    else:
        print("Failed to create admin user.")