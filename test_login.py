import bcrypt
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables (will pick up DATABASE_URL from .env for local testing)
load_dotenv()

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

def test_admin_login(username, password):
    """Test admin login"""
    conn = None  # Initialize conn to None for the finally block
    cursor = None # Initialize cursor to None for the finally block
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("Error: DATABASE_URL environment variable not set.")
            return False
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Get admin user
        cursor.execute("""
            SELECT id, username, email, password_hash, user_type
            FROM users
            WHERE username = %s AND user_type = 'admin'
        """, (username,))
        
        user = cursor.fetchone()
        
        if user:
            user_id, username, email, password_hash, user_type = user
            
            # Test password
            if verify_password(password_hash, password):
                print(f"Login successful for admin user: {username}")
                return True
            else:
                print(f"Invalid password for admin user: {username}")
                return False
        else:
            print(f"Admin user not found: {username}")
            return False
    
    except Exception as e:
        print(f"Error testing admin login: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Test admin login
    admin_username = "admin"
    admin_password = "admin123"
    
    print(f"Testing login for admin user: {admin_username}")
    success = test_admin_login(admin_username, admin_password)
    
    if success:
        print("\nAdmin login test successful!")
        print(f"Username: {admin_username}")
        print(f"Password: {admin_password}")
    else:
        print("\nAdmin login test failed.")