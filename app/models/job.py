import psycopg2
import psycopg2.extras
from app.database.connection import get_connection
from .match import Match # If needed for direct Match object creation, but not for this version

class Job:
    def __init__(self, id=None, job_giver_id=None, title=None, description=None, 
                 requirements=None, location=None, salary_range=None, job_type=None, 
                 created_at=None, active=True):
        self.id = id
        self.job_giver_id = job_giver_id
        self.title = title
        self.description = description
        self.requirements = requirements or []
        self.location = location
        self.salary_range = salary_range
        self.job_type = job_type
        self.created_at = created_at
        self.active = active
    
    def create(self):
        """Create a new job listing"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO jobs 
                (job_giver_id, title, description, requirements, location, 
                 salary_range, job_type, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
                """,
                (self.job_giver_id, self.title, self.description, self.requirements, 
                 self.location, self.salary_range, self.job_type, self.active)
            )
            
            job_id, created_at = cursor.fetchone()
            conn.commit()
            
            self.id = job_id
            self.created_at = created_at
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error creating job: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_id(job_id):
        """Get a job by ID"""
        conn = get_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, job_giver_id, title, description, requirements, 
                       location, salary_range, job_type, created_at, active
                FROM jobs
                WHERE id = %s
                """,
                (job_id,)
            )
            
            job_data = cursor.fetchone()
            if job_data:
                return Job(
                    id=job_data[0],
                    job_giver_id=job_data[1],
                    title=job_data[2],
                    description=job_data[3],
                    requirements=job_data[4],
                    location=job_data[5],
                    salary_range=job_data[6],
                    job_type=job_data[7],
                    created_at=job_data[8],
                    active=job_data[9]
                )
            return None
        except psycopg2.Error as e:
            print(f"Error getting job: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_by_job_giver_id(job_giver_id):
        """Get all jobs for a job giver"""
        conn = None
        try:
            conn = get_connection()
            if conn is None:
                print("Failed to get database connection")
                return []

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, job_giver_id, title, description, requirements, 
                       location, salary_range, job_type, created_at, active
                FROM jobs
                WHERE job_giver_id = %s
                ORDER BY created_at DESC
                """,
                (job_giver_id,)
            )
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append(Job(
                    id=row[0],
                    job_giver_id=row[1],
                    title=row[2],
                    description=row[3],
                    requirements=row[4],
                    location=row[5],
                    salary_range=row[6],
                    job_type=row[7],
                    created_at=row[8],
                    active=row[9]
                ))
            
            return jobs
        except Exception as e:
            print(f"Error getting jobs for job giver {job_giver_id}: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def get_all_for_swiping(job_seeker_id, limit=10, keywords=None, location=None, job_type=None, min_salary=None, max_salary=None):
        """
        Get jobs for swiping, excluding those already swiped, with optional search filters
        
        Args:
            job_seeker_id: ID of the job seeker
            limit: Maximum number of jobs to return
            keywords: Search terms for job title or description
            location: Job location to filter by
            job_type: Type of job (Full-time, Part-time, etc.)
            min_salary: Minimum salary (extracted from salary_range)
            max_salary: Maximum salary (extracted from salary_range)
        """
        conn = get_connection()
        if conn is None:
            return []
        
        try:
            # Build the query with optional filters
            query = """
                SELECT j.id, j.job_giver_id, j.title, j.description, j.requirements, 
                       j.location, j.salary_range, j.job_type, j.created_at, j.active,
                       jg.company_name
                FROM jobs j
                JOIN job_givers jg ON j.job_giver_id = jg.id
                WHERE j.active = TRUE
                AND j.id NOT IN (
                    SELECT target_id::integer FROM swipes 
                    WHERE user_id = (SELECT user_id FROM job_seekers WHERE id = %s)
                    AND target_type = 'job'
                    AND direction = 'right'
                )
            """
            
            params = [job_seeker_id]
            
            # Add keyword search (title or description)
            if keywords:
                query += " AND (j.title ILIKE %s OR j.description ILIKE %s)"
                keywords_param = f"%{keywords}%"
                params.extend([keywords_param, keywords_param])
            
            # Add location filter
            if location:
                query += " AND j.location ILIKE %s"
                params.append(f"%{location}%")
            
            # Add job type filter
            if job_type:
                query += " AND j.job_type = %s"
                params.append(job_type)
            
            # Add salary range filters (this is approximate since salary is stored as text)
            # In a production app, you'd store min and max salary as separate numeric fields
            if min_salary:
                query += " AND j.salary_range LIKE %s"
                params.append(f"%{min_salary}%")
            
            if max_salary:
                query += " AND j.salary_range LIKE %s"
                params.append(f"%{max_salary}%")
            
            # Add limit
            query += " LIMIT %s"
            params.append(limit)
            
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            jobs = []
            for row in cursor.fetchall():
                job = Job(
                    id=row[0],
                    job_giver_id=row[1],
                    title=row[2],
                    description=row[3],
                    requirements=row[4],
                    location=row[5],
                    salary_range=row[6],
                    job_type=row[7],
                    created_at=row[8],
                    active=row[9]
                )
                job.company_name = row[10]  # Add company name for display
                jobs.append(job)
            
            return jobs
        except psycopg2.Error as e:
            print(f"Error getting jobs for swiping: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def update(self):
        """Update job details"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET title = %s, description = %s, requirements = %s, 
                    location = %s, salary_range = %s, job_type = %s, active = %s
                WHERE id = %s
                """,
                (self.title, self.description, self.requirements, 
                 self.location, self.salary_range, self.job_type, 
                 self.active, self.id)
            )
            
            conn.commit()
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating job: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    @classmethod
    def get_potential_applicants(cls, job_id, job_giver_id):
        """
        Gets all job seekers who swiped right on a job, along with their match status
        with the given job_giver.
        """
        conn = get_connection()
        applicants_data = []
        if not conn:
            print("Failed to get database connection in get_potential_applicants.")
            return applicants_data
        
        try:
            # Use DictCursor for easier access to columns by name
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # SQL to get job seekers who swiped right on this job
            sql_potential_applicants = """
                SELECT
                    s.user_id AS swiper_user_id,
                    s.created_at AS application_date,
                    js.id AS job_seeker_id,
                    js.full_name AS applicant_name,
                    js.experience AS applicant_experience,
                    js.location AS applicant_location,
                    js.education AS applicant_education,
                    js.skills AS applicant_skills,
                    js.bio AS applicant_bio,
                    js.cv_path AS applicant_cv_path,
                    u.email AS applicant_email
                FROM swipes s
                JOIN users u ON s.user_id = u.id
                JOIN job_seekers js ON u.id = js.user_id
                WHERE s.target_id = %s       -- job_id
                  AND s.target_type = 'job'
                  AND s.direction = 'right'
                  AND u.user_type = 'job_seeker'
                ORDER BY s.created_at DESC;
            """
            cursor.execute(sql_potential_applicants, (job_id,))
            potential_applicants_rows = cursor.fetchall()

            for pa_row in potential_applicants_rows:
                # Check for an existing match with the current job_giver for this job and seeker
                sql_match_check = """
                    SELECT id, status, created_at AS match_created_at
                    FROM matches
                    WHERE job_id = %s
                      AND job_seeker_id = %s
                      AND job_giver_id = %s;
                """
                cursor.execute(sql_match_check, (job_id, pa_row['job_seeker_id'], job_giver_id))
                match_info = cursor.fetchone()

                applicant_detail_dict = {
                    "job_seeker_id": pa_row['job_seeker_id'],
                    "user_id": pa_row['swiper_user_id'], # Job Seeker's user_id from users table
                    "applicant_name": pa_row['applicant_name'],
                    "applicant_experience": pa_row['applicant_experience'],
                    "applicant_location": pa_row['applicant_location'],
                    "applicant_education": pa_row['applicant_education'],
                    "applicant_skills": pa_row['applicant_skills'] or [], # Ensure skills is a list
                    "applicant_bio": pa_row['applicant_bio'],
                    "applicant_cv_path": pa_row['applicant_cv_path'],
                    "applicant_email": pa_row['applicant_email'],
                    "application_date": pa_row['application_date'], # When they swiped on the job
                    "is_matched": bool(match_info),
                    "match_id": match_info['id'] if match_info else None,
                    "match_status": match_info['status'] if match_info else "applied",
                    "match_created_at": match_info['match_created_at'] if match_info else None
                }
                # Convert dict to an object for easier attribute access (e.g., applicant.applicant_name)
                applicants_data.append(type('ApplicantDetails', (object,), applicant_detail_dict)())
        
        except psycopg2.Error as db_err:
            print(f"Database error in Job.get_potential_applicants: {db_err}")
            # conn.rollback() # Not strictly necessary for SELECTs but good practice if there were writes
        except Exception as e:
            print(f"General error in Job.get_potential_applicants: {e}")
        finally:
            if conn:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                conn.close()
        return applicants_data
    
    def deactivate(self):
        """Deactivate a job listing"""
        self.active = False
        return self.update()
        
    def activate(self):
        """Activate a job listing"""
        self.active = True
        return self.update()
        
    @staticmethod
    def set_active_status(job_id, active_status):
        """Set the active status of a job"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE jobs
                SET active = %s
                WHERE id = %s
                """,
                (active_status, job_id)
            )
            
            conn.commit()
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating job active status: {e}")
            return False
        finally:
            cursor.close()
            conn.close()