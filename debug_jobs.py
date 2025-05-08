import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables (will pick up DATABASE_URL from .env for local testing)
load_dotenv()

def get_connection():
    """Create a connection to the PostgreSQL database"""
    try:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("Error: DATABASE_URL environment variable not set.")
            print("Ensure it's in your .env file for local use or set by your deployment environment.")
            return None
        conn = psycopg2.connect(database_url)
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None

def debug_jobs_and_swipes():
    """Debug jobs and swipes"""
    conn = get_connection()
    if conn is None:
        print("Failed to connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get all jobs
        cursor.execute("""
            SELECT id, title, active
            FROM jobs
            ORDER BY id
        """)
        
        jobs = cursor.fetchall()
        print("\n=== JOBS IN DATABASE ===")
        print(f"Total jobs: {len(jobs)}")
        for job in jobs:
            job_id, title, active = job
            print(f"- ID: {job_id}, Title: {title}, Active: {active}")
        
        # Get all swipes
        cursor.execute("""
            SELECT id, user_id, target_id, target_type, direction
            FROM swipes
            ORDER BY id
        """)
        
        swipes = cursor.fetchall()
        print("\n=== SWIPES IN DATABASE ===")
        print(f"Total swipes: {len(swipes)}")
        for swipe in swipes:
            swipe_id, user_id, target_id, target_type, direction = swipe
            print(f"- ID: {swipe_id}, User ID: {user_id}, Target ID: {target_id}, Type: {target_type}, Direction: {direction}")
        
        # Get all job seekers
        cursor.execute("""
            SELECT id, user_id, full_name
            FROM job_seekers
            ORDER BY id
        """)
        
        job_seekers = cursor.fetchall()
        print("\n=== JOB SEEKERS IN DATABASE ===")
        print(f"Total job seekers: {len(job_seekers)}")
        for seeker in job_seekers:
            seeker_id, user_id, full_name = seeker
            print(f"- ID: {seeker_id}, User ID: {user_id}, Name: {full_name}")
        
        # For each job seeker, check which jobs they would see
        print("\n=== JOBS AVAILABLE FOR SWIPING ===")
        for seeker in job_seekers:
            seeker_id, user_id, full_name = seeker
            
            # This is the query from Job.get_all_for_swiping
            cursor.execute("""
                SELECT j.id, j.title
                FROM jobs j
                JOIN job_givers jg ON j.job_giver_id = jg.id
                WHERE j.active = TRUE
                AND j.id NOT IN (
                    SELECT target_id::integer FROM swipes 
                    WHERE user_id = (SELECT user_id FROM job_seekers WHERE id = %s)
                    AND target_type = 'job'
                    AND direction = 'right'
                )
            """, (seeker_id,))
            
            available_jobs = cursor.fetchall()
            print(f"\nJob seeker: {full_name} (ID: {seeker_id}, User ID: {user_id})")
            print(f"Available jobs for swiping: {len(available_jobs)}")
            for job in available_jobs:
                job_id, title = job
                print(f"- ID: {job_id}, Title: {title}")
            
            # Check if there are any inactive jobs
            cursor.execute("""
                SELECT COUNT(*) FROM jobs WHERE active = FALSE
            """)
            inactive_count = cursor.fetchone()[0]
            print(f"Inactive jobs count: {inactive_count}")
            
            # Check if there are any jobs with issues
            cursor.execute("""
                SELECT j.id, j.title, j.active
                FROM jobs j
                WHERE j.id NOT IN (
                    SELECT j.id
                    FROM jobs j
                    JOIN job_givers jg ON j.job_giver_id = jg.id
                    WHERE j.active = TRUE
                )
            """)
            
            problem_jobs = cursor.fetchall()
            if problem_jobs:
                print("\n=== JOBS WITH POTENTIAL ISSUES ===")
                for job in problem_jobs:
                    job_id, title, active = job
                    print(f"- ID: {job_id}, Title: {title}, Active: {active}")
                
                # Check job_givers table
                cursor.execute("""
                    SELECT id, user_id, company_name
                    FROM job_givers
                """)
                
                job_givers = cursor.fetchall()
                print("\n=== JOB GIVERS IN DATABASE ===")
                for giver in job_givers:
                    giver_id, user_id, company_name = giver
                    print(f"- ID: {giver_id}, User ID: {user_id}, Company: {company_name}")
                
                # Check jobs with missing job_givers
                cursor.execute("""
                    SELECT j.id, j.title, j.job_giver_id
                    FROM jobs j
                    LEFT JOIN job_givers jg ON j.job_giver_id = jg.id
                    WHERE jg.id IS NULL
                """)
                
                orphaned_jobs = cursor.fetchall()
                if orphaned_jobs:
                    print("\n=== JOBS WITH MISSING JOB GIVERS ===")
                    for job in orphaned_jobs:
                        job_id, title, job_giver_id = job
                        print(f"- ID: {job_id}, Title: {title}, Job Giver ID: {job_giver_id}")
    
    except psycopg2.Error as e:
        print(f"Error debugging jobs and swipes: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    debug_jobs_and_swipes()