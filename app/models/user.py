import psycopg2
import psycopg2.extras # For DictCursor in new methods
import bcrypt
from app.database.connection import get_connection

class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None, 
                 user_type=None, created_at=None, is_active=True): # Added is_active
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.user_type = user_type
        self.created_at = created_at
        self.is_active = is_active # Initialize is_active
    
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
        print(f"Starting user creation for username: {username}")
        conn = get_connection()
        if conn is None:
            print("Failed to get database connection during user creation")
            return None
        
        try:
            cursor = conn.cursor()
            print("Creating password hash...")
            password_hash = User.hash_password(password)
            
            print("Inserting user into database...")
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, user_type, is_active)
                VALUES (%s, %s, %s, %s, TRUE) -- is_active defaults to TRUE in DB, explicit here
                RETURNING id, created_at, is_active
                """,
                (username, email, password_hash, user_type)
            )
            
            user_id, created_at, is_active_db = cursor.fetchone()
            print(f"User created with ID: {user_id}")
            conn.commit()
            
            # Create corresponding profile based on user type
            print(f"Creating {user_type} profile...")
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
            print(f"Profile creation successful for {user_type}")
            
            return User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                user_type=user_type,
                created_at=created_at,
                is_active=is_active_db # Set is_active from DB result
            )
        except psycopg2.Error as e:
            conn.rollback()
            print(f"DATABASE ERROR in User.create for {username}:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {e}")
            print(f"Error code: {e.pgcode if hasattr(e, 'pgcode') else 'N/A'}")
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
            return None
        except Exception as ex:
            conn.rollback()
            print(f"UNEXPECTED ERROR in User.create for {username}:")
            print(f"Error type: {type(ex).__name__}")
            print(f"Error message: {ex}")
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
            return None
        finally:
            cursor.close()
            conn.close()
            print("Database connection closed")
    
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
                SELECT id, username, email, password_hash, user_type, created_at, is_active
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
                    created_at=user_data[5],
                    is_active=user_data[6] # Added is_active
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
                SELECT id, username, email, password_hash, user_type, created_at, is_active
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
                    created_at=user_data[5],
                    is_active=user_data[6] # Added is_active
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
        """
        Authenticates a user.
        Returns User object if authentication is successful and user is active.
        Returns the string "suspended" if user is suspended.
        Returns None if authentication fails (user not found or password mismatch).
        """
        user = User.get_by_username(username)
        if user and not user.is_active:
            return "suspended" # Account is suspended
        if user and user.is_active and User.verify_password(user.password_hash, password):
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
                SELECT id, username, email, password_hash, user_type, created_at, is_active
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
                    created_at=user_data[5],
                    is_active=user_data[6] # Added is_active
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
    def get_all_managed_users():
        """Retrieves all users for management purposes."""
        conn = get_connection()
        if not conn:
            print("Database connection failed in get_all_managed_users")
            return []
        users_list = []
        try:
            # Using DictCursor here for easier access to column names
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT id, username, email, user_type, is_active, created_at 
                    FROM users 
                    ORDER BY username
                """)
                for row in cur.fetchall():
                    users_list.append(dict(row)) # Convert Row objects to dicts
        except psycopg2.Error as e:
            print(f"Database error fetching all users: {e}")
        finally:
            if conn:
                conn.close()
        return users_list

    @staticmethod
    def set_active_status(user_id, is_active_bool):
        """Sets the is_active status for a user."""
        conn = get_connection()
        if not conn:
            print(f"Database connection failed while trying to set active status for user {user_id}")
            return False
        updated_rows = 0
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET is_active = %s WHERE id = %s", (is_active_bool, user_id))
                updated_rows = cur.rowcount
                conn.commit()
        except psycopg2.Error as e:
            print(f"Database error setting user active status for user_id {user_id}: {e}")
            conn.rollback()
        finally:
            if conn:
                conn.close()
        return updated_rows > 0

    @staticmethod
    def delete_user_by_id(user_id_to_delete, current_admin_id):
        """
        Deletes a user and their associated data.
        Prevents admin from deleting themselves.
        """
        if int(user_id_to_delete) == int(current_admin_id):
            return False, "Admin cannot delete themselves."

        conn = get_connection()
        if not conn:
            return False, "Database connection failed."

        try:
            # Use DictCursor for easier access to user_type and job_ids
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Get user type to determine which related tables to clean
                cur.execute("SELECT user_type FROM users WHERE id = %s", (user_id_to_delete,))
                user_record = cur.fetchone()
                if not user_record:
                    return False, "User not found."
                user_type = user_record['user_type']

                print(f"Attempting to delete user ID: {user_id_to_delete}, Type: {user_type}")

                # 1. Delete from swipes (where this user initiated the swipe)
                cur.execute("DELETE FROM swipes WHERE user_id = %s", (user_id_to_delete,))
                print(f"Deleted {cur.rowcount} swipes initiated by user_id {user_id_to_delete}")

                # 2. Delete from job_seekers or job_givers profile tables & related data
                if user_type == 'job_seeker':
                    # Future: Consider deleting matches involving this job_seeker_id if a matches table exists
                    # cur.execute("DELETE FROM matches WHERE job_seeker_id = (SELECT id FROM job_seekers WHERE user_id = %s)", (user_id_to_delete,))
                    cur.execute("DELETE FROM job_seekers WHERE user_id = %s", (user_id_to_delete,))
                    print(f"Deleted job_seeker profile for user_id {user_id_to_delete} (if existed)")

                elif user_type == 'job_giver':
                    cur.execute("SELECT id FROM job_givers WHERE user_id = %s", (user_id_to_delete,))
                    jg_profile = cur.fetchone()
                    if jg_profile:
                        job_giver_id = jg_profile['id']
                        
                        # Get all jobs by this job_giver
                        cur.execute("SELECT id FROM jobs WHERE job_giver_id = %s", (job_giver_id,))
                        jobs_to_delete = cur.fetchall() # List of row objects (DictRow)
                        job_ids_to_delete = [job['id'] for job in jobs_to_delete]

                        if job_ids_to_delete:
                            # Delete swipes targeting these jobs.
                            # Assuming target_id in swipes for jobs is stored as text representation of job.id
                            job_ids_as_text = [str(jid) for jid in job_ids_to_delete]
                            cur.execute("""
                                DELETE FROM swipes 
                                WHERE target_type = 'job' AND target_id = ANY(%s::text[])
                            """, (job_ids_as_text,))
                            print(f"Deleted {cur.rowcount} swipes targeting jobs of job_giver_id {job_giver_id}")
                            
                            # Future: Consider deleting matches involving these job_ids if a matches table exists
                            # cur.execute("DELETE FROM matches WHERE job_id = ANY(%s)", (job_ids_to_delete,))

                        # Delete jobs posted by this job_giver
                        cur.execute("DELETE FROM jobs WHERE job_giver_id = %s", (job_giver_id,))
                        print(f"Deleted {cur.rowcount} jobs for job_giver_id {job_giver_id}")

                    cur.execute("DELETE FROM job_givers WHERE user_id = %s", (user_id_to_delete,))
                    print(f"Deleted job_giver profile for user_id {user_id_to_delete} (if existed)")

                # 3. Finally, delete from users table
                cur.execute("DELETE FROM users WHERE id = %s", (user_id_to_delete,))
                deleted_user_count = cur.rowcount
                print(f"Deleted {deleted_user_count} user from users table, id {user_id_to_delete}")

                conn.commit()
                return True, "User deleted successfully."
        except psycopg2.Error as e:
            print(f"Database error deleting user_id {user_id_to_delete}: {e}")
            conn.rollback()
            return False, f"Error deleting user: {e}"
        finally:
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