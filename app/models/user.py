import psycopg2
import bcrypt
from app.database.connection import get_connection

class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None, user_type=None, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.user_type = user_type
        self.created_at = created_at
    
    @staticmethod
    def hash_password(password):
        """Hash a password for storing"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(stored_password, provided_password):
        """Verify a stored password against one provided by user"""
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))
    
    @staticmethod
    def create(username, email, password, user_type):
        """Create a new user"""
        conn = get_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            password_hash = User.hash_password(password)
            
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, user_type)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at
                """,
                (username, email, password_hash, user_type)
            )
            
            user_id, created_at = cursor.fetchone()
            conn.commit()
            
            # Create corresponding profile based on user type
            if user_type == 'job_seeker':
                cursor.execute(
                    """
                    INSERT INTO job_seekers (user_id, credits)
                    VALUES (%s, 0)
                    """,
                    (user_id,)
                )
            elif user_type == 'job_giver':
                cursor.execute(
                    """
                    INSERT INTO job_givers (user_id, credits)
                    VALUES (%s, 0)
                    """,
                    (user_id,)
                )
            
            conn.commit()
            
            return User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                user_type=user_type,
                created_at=created_at
            )
        except psycopg2.Error as e:
            conn.rollback()
            print(f"DATABASE ERROR in User.create for {username}: {type(e).__name__} - {e}")
            import traceback
            print(traceback.format_exc())
            return None
        except Exception as ex: # Catch any other unexpected error during user creation
            conn.rollback()
            print(f"UNEXPECTED ERROR in User.create for {username}: {type(ex).__name__} - {ex}")
            import traceback
            print(traceback.format_exc())
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_username(username):
        """Get a user by username"""
        conn = get_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, email, password_hash, user_type, created_at
                FROM users
                WHERE username = %s
                """,
                (username,)
            )
            
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    email=user_data[2],
                    password_hash=user_data[3],
                    user_type=user_data[4],
                    created_at=user_data[5]
                )
            return None
        except psycopg2.Error as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_id(user_id):
        """Get a user by ID"""
        conn = get_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, email, password_hash, user_type, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    email=user_data[2],
                    password_hash=user_data[3],
                    user_type=user_data[4],
                    created_at=user_data[5]
                )
            return None
        except psycopg2.Error as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def authenticate(username, password):
        """Authenticate a user"""
        user = User.get_by_username(username)
        if user and User.verify_password(user.password_hash, password):
            return user
        return None

    @staticmethod
    def get_by_username_and_email(username, email):
        """Get a user by username and email."""
        conn = get_connection()
        if conn is None:
            print("Database connection error in get_by_username_and_email")
            return None
        
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, email, password_hash, user_type, created_at
                FROM users
                WHERE username = %s AND LOWER(email) = LOWER(%s)
                """,
                (username, email)
            )
            
            user_data = cursor.fetchone()
            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    email=user_data[2],
                    password_hash=user_data[3],
                    user_type=user_data[4],
                    created_at=user_data[5]
                )
            return None
        except psycopg2.Error as e:
            print(f"Error getting user by username and email: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def update_password_by_username(username, new_password):
        """Update user's password by username."""
        conn = get_connection()
        if conn is None:
            print("Database connection error in update_password_by_username")
            return False
        
        cursor = None
        try:
            cursor = conn.cursor()
            new_password_hash = User.hash_password(new_password)
            
            cursor.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE username = %s
                """,
                (new_password_hash, username)
            )
            
            updated_rows = cursor.rowcount
            conn.commit()
            return updated_rows > 0
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating password for user {username}: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()