import os
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "jobmatch")

def get_connection():
    """Create a connection to the PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None

def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"Database {DB_NAME} created successfully")
        
        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")

def init_tables():
    """Initialize database tables"""
    conn = get_connection()
    if conn is None:
        return
    
    try:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            user_type VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create job_seekers table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_seekers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            full_name VARCHAR(100),
            bio TEXT,
            skills TEXT[],
            experience INTEGER,
            education TEXT,
            location VARCHAR(100),
            cv_path VARCHAR(255),
            credits INTEGER DEFAULT 0,
            profile_complete BOOLEAN DEFAULT FALSE
        )
        """)
        
        # Create job_givers table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_givers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            company_name VARCHAR(100),
            company_description TEXT,
            website VARCHAR(255),
            location VARCHAR(100),
            credits INTEGER DEFAULT 0,
            profile_complete BOOLEAN DEFAULT FALSE
        )
        """)
        
        # Create jobs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            job_giver_id INTEGER REFERENCES job_givers(id) ON DELETE CASCADE,
            title VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            requirements TEXT[],
            location VARCHAR(100),
            salary_range VARCHAR(100),
            job_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN DEFAULT TRUE
        )
        """)
        
        # Create swipes table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS swipes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            target_id INTEGER NOT NULL,
            target_type VARCHAR(20) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Check if job_id column exists in swipes table
        cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='swipes' AND column_name='job_id'
        """)
        
        job_id_column_exists = cursor.fetchone() is not None
        
        # Add job_id column if it doesn't exist
        if not job_id_column_exists:
            try:
                cursor.execute("""
                ALTER TABLE swipes 
                ADD COLUMN job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE
                """)
                print("Added job_id column to swipes table")
            except Exception as e:
                print(f"Error adding job_id column: {e}")
                # Continue even if this fails - the application will handle missing column
        
        # Create matches table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            job_seeker_id INTEGER REFERENCES job_seekers(id) ON DELETE CASCADE,
            job_giver_id INTEGER REFERENCES job_givers(id) ON DELETE CASCADE,
            job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) DEFAULT 'active'
        )
        """)
        
        # Create credit_transactions table
        # Note: price_inr is NUMERIC(10, 2) to store currency values accurately.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_packages (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            credits_amount INTEGER NOT NULL,
            price_inr NUMERIC(10, 2) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create credit_transactions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            amount INTEGER NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create redemption_requests table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS redemption_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            job_seeker_id INTEGER REFERENCES job_seekers(id) ON DELETE CASCADE,
            amount INTEGER NOT NULL,
            upi_id VARCHAR(100) NOT NULL,
            whatsapp_number VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        )
        """)
        
        # Create admin user if it doesn't exist
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, user_type)
        SELECT 'admin', 'admin@jobmatch.com', '$2b$12$tPpS/hYvGQsXWQQ/XUvUxeQBs1VdGj9A.QQwjwwP5Ij.OQ8QrJZ0y', 'admin'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin')
        """)
        
        conn.commit()
        print("Database tables initialized successfully")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error initializing tables: {e}")
    finally:
        cursor.close()
        conn.close()

def init_db():
    """Initialize the database and tables"""
    try:
        create_database_if_not_exists()
        init_tables()
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("Database connection failed. The app will run in demo mode with limited functionality.")
        return False

if __name__ == "__main__":
    init_db()