import psycopg2
from app.database.connection import get_connection

class Match:
    def __init__(self, id=None, job_seeker_id=None, job_giver_id=None, job_id=None, 
                 created_at=None, status=None):
        self.id = id
        self.job_seeker_id = job_seeker_id
        self.job_giver_id = job_giver_id
        self.job_id = job_id
        self.created_at = created_at
        self.status = status or 'active'
    
    @staticmethod
    def get_by_id(match_id):
        """Get a match by ID"""
        conn = get_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, job_seeker_id, job_giver_id, job_id, created_at, status
                FROM matches
                WHERE id = %s
                """,
                (match_id,)
            )
            
            match_data = cursor.fetchone()
            if match_data:
                return Match(
                    id=match_data[0],
                    job_seeker_id=match_data[1],
                    job_giver_id=match_data[2],
                    job_id=match_data[3],
                    created_at=match_data[4],
                    status=match_data[5]
                )
            return None
        except psycopg2.Error as e:
            print(f"Error getting match: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_for_job_seeker(job_seeker_id):
        """Get all matches for a job seeker"""
        conn = get_connection()
        if conn is None:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.id, m.job_seeker_id, m.job_giver_id, m.job_id, 
                       m.created_at, m.status,
                       j.title, jg.company_name
                FROM matches m
                JOIN jobs j ON m.job_id = j.id
                JOIN job_givers jg ON m.job_giver_id = jg.id
                WHERE m.job_seeker_id = %s
                ORDER BY m.created_at DESC
                """,
                (job_seeker_id,)
            )
            
            matches = []
            for row in cursor.fetchall():
                match = Match(
                    id=row[0],
                    job_seeker_id=row[1],
                    job_giver_id=row[2],
                    job_id=row[3],
                    created_at=row[4],
                    status=row[5]
                )
                match.job_title = row[6]
                match.company_name = row[7]
                matches.append(match)
            
            # Print for debugging
            print(f"Found {len(matches)} matches for job seeker {job_seeker_id}")
            
            return matches
        except psycopg2.Error as e:
            print(f"Error getting matches for job seeker: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_for_job_giver(job_giver_id):
        """Get all matches for a job giver"""
        conn = get_connection()
        if conn is None:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.id, m.job_seeker_id, m.job_giver_id, m.job_id, 
                       m.created_at, m.status,
                       j.title, js.full_name
                FROM matches m
                JOIN jobs j ON m.job_id = j.id
                JOIN job_seekers js ON m.job_seeker_id = js.id
                WHERE m.job_giver_id = %s
                ORDER BY m.created_at DESC
                """,
                (job_giver_id,)
            )
            
            matches = []
            for row in cursor.fetchall():
                match = Match(
                    id=row[0],
                    job_seeker_id=row[1],
                    job_giver_id=row[2],
                    job_id=row[3],
                    created_at=row[4],
                    status=row[5]
                )
                match.job_title = row[6]
                match.job_seeker_name = row[7]
                matches.append(match)
            
            # Print for debugging
            print(f"Found {len(matches)} matches for job giver {job_giver_id}")
            
            return matches
        except psycopg2.Error as e:
            print(f"Error getting matches for job giver: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_applicants_for_job(job_id):
        """Get all applicants (job seekers) who matched with a specific job"""
        conn = get_connection()
        if conn is None:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.id, m.job_seeker_id, m.job_giver_id, m.job_id, 
                       m.created_at, m.status,
                       js.full_name, js.skills, js.experience, js.education, js.location
                FROM matches m
                JOIN job_seekers js ON m.job_seeker_id = js.id
                WHERE m.job_id = %s
                ORDER BY m.created_at DESC
                """,
                (job_id,)
            )
            
            applicants = []
            for row in cursor.fetchall():
                match = Match(
                    id=row[0],
                    job_seeker_id=row[1],
                    job_giver_id=row[2],
                    job_id=row[3],
                    created_at=row[4],
                    status=row[5]
                )
                match.applicant_name = row[6]
                match.applicant_skills = row[7]
                match.applicant_experience = row[8]
                match.applicant_education = row[9]
                match.applicant_location = row[10]
                applicants.append(match)
            
            # Print for debugging
            print(f"Found {len(applicants)} applicants for job {job_id}")
            
            return applicants
        except psycopg2.Error as e:
            print(f"Error getting applicants for job: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    @staticmethod
    def update_status_by_id(match_id, new_status):
        """Updates the status of a match given its ID."""
        conn = get_connection()
        if not conn or not match_id:
            print("Failed to update match status: No connection or match_id.")
            return False
        
        success = False
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE matches SET status = %s, updated_at = NOW() WHERE id = %s", 
                (new_status, match_id)
            )
            conn.commit()
            success = cursor.rowcount > 0
            if not success:
                print(f"Match status update: No row found for match_id {match_id}")
        except psycopg2.Error as db_err:
            print(f"Database error updating match status by ID {match_id}: {db_err}")
            conn.rollback()
        except Exception as e:
            print(f"General error updating match status by ID {match_id}: {e}")
            conn.rollback() # Rollback on general error too
        finally:
            if conn:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                conn.close()
        return success
        
    def update_status(self, new_status):
        """Update match status"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE matches
                SET status = %s
                WHERE id = %s
                """,
                (new_status, self.id)
            )
            
            conn.commit()
            self.status = new_status
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating match status: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
