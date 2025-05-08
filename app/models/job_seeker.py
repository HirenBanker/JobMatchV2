import psycopg2
from app.database.connection import get_connection

class JobSeeker:
    def __init__(self, id=None, user_id=None, full_name=None, bio=None, skills=None, 
                 experience=None, education=None, location=None, cv_path=None, 
                 credits=0, profile_complete=False):
        self.id = id
        self.user_id = user_id
        self.full_name = full_name
        self.bio = bio
        self.skills = skills or []
        self.experience = experience
        self.education = education
        self.location = location
        self.cv_path = cv_path
        self.credits = credits
        self.profile_complete = profile_complete
    
    @staticmethod
    def get_by_user_id(user_id):
        """Get a job seeker by user ID"""
        conn = get_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, full_name, bio, skills, experience, education, 
                       location, cv_path, credits, profile_complete
                FROM job_seekers
                WHERE user_id = %s
                """,
                (user_id,)
            )
            
            seeker_data = cursor.fetchone()
            if seeker_data:
                return JobSeeker(
                    id=seeker_data[0],
                    user_id=seeker_data[1],
                    full_name=seeker_data[2],
                    bio=seeker_data[3],
                    skills=seeker_data[4],
                    experience=seeker_data[5],
                    education=seeker_data[6],
                    location=seeker_data[7],
                    cv_path=seeker_data[8],
                    credits=seeker_data[9],
                    profile_complete=seeker_data[10]
                )
            return None
        except psycopg2.Error as e:
            print(f"Error getting job seeker: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def update_profile(self):
        """Update job seeker profile"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE job_seekers
                SET full_name = %s, bio = %s, skills = %s, experience = %s, 
                    education = %s, location = %s, cv_path = %s, profile_complete = %s
                WHERE user_id = %s
                RETURNING id
                """,
                (self.full_name, self.bio, self.skills, self.experience, 
                 self.education, self.location, self.cv_path, 
                 True, self.user_id)
            )
            
            updated_id = cursor.fetchone()[0]
            conn.commit()
            self.id = updated_id
            self.profile_complete = True
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating job seeker profile: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all_for_swiping(job_giver_id, limit=10, skills=None, min_experience=None, location=None, education=None, job_id=None):
        """
        Get job seekers for swiping, excluding those already swiped, with optional search filters
        
        Args:
            job_giver_id: ID of the job giver
            limit: Maximum number of job seekers to return
            skills: Specific skills to filter by (list or comma-separated string)
            min_experience: Minimum years of experience
            location: Location to filter by
            education: Education level or institution to filter by
            job_id: Optional specific job ID to filter candidates for
        """
        conn = get_connection()
        if conn is None:
            return []
        
        try:
            # Build the query with optional filters
            query = """
                SELECT js.id, js.user_id, js.full_name, js.bio, js.skills, 
                       js.experience, js.education, js.location, js.credits
                FROM job_seekers js
                JOIN users u ON js.user_id = u.id
                WHERE js.profile_complete = TRUE
            """
            
            params = []
            
            # First, check if the job_id column exists in the swipes table
            cursor = conn.cursor()
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='swipes' AND column_name='job_id'
            """)
            
            job_id_column_exists = cursor.fetchone() is not None
            
            # If a specific job ID is provided, only exclude candidates already swiped for this job
            if job_id and job_id_column_exists:
                query += """
                    AND js.id NOT IN (
                        SELECT target_id::integer FROM swipes 
                        WHERE user_id = (SELECT user_id FROM job_givers WHERE id = %s)
                        AND target_type = 'job_seeker'
                        AND direction = 'right'
                        AND job_id = %s
                    )
                """
                params.extend([job_giver_id, job_id])
            elif job_id:
                # If job_id is provided but the column doesn't exist yet, use a simpler query
                print("job_id column doesn't exist yet, using simpler query")
                query += """
                    AND js.id NOT IN (
                        SELECT target_id::integer FROM swipes 
                        WHERE user_id = (SELECT user_id FROM job_givers WHERE id = %s)
                        AND target_type = 'job_seeker'
                        AND direction = 'right'
                    )
                """
                params.append(job_giver_id)
            else:
                # No job_id provided: exclude all candidates swiped right on for any job
                query += """
                    AND js.id NOT IN (
                        SELECT target_id::integer FROM swipes 
                        WHERE user_id = (SELECT user_id FROM job_givers WHERE id = %s)
                        AND target_type = 'job_seeker'
                        AND direction = 'right'
                    )
                """
                params.append(job_giver_id)
            
            # Also exclude candidates that are already matched with this job giver for this job
            if job_id:
                query += """
                    AND js.id NOT IN (
                        SELECT job_seeker_id FROM matches
                        WHERE job_giver_id = %s
                        AND job_id = %s
                    )
                """
                params.extend([job_giver_id, job_id])
            
            # This line was causing the error - we don't need to add job_giver_id again
            # params.append(job_giver_id)
            
            # Add skills filter
            if skills:
                # Convert string to list if needed
                if isinstance(skills, str):
                    skills_list = [s.strip() for s in skills.split(',')]
                else:
                    skills_list = skills
                
                # For each skill, check if it's in the skills array
                for skill in skills_list:
                    query += " AND %s = ANY(js.skills)"
                    params.append(skill)
            
            # Add minimum experience filter
            if min_experience is not None:
                query += " AND js.experience >= %s"
                params.append(min_experience)
            
            # Add location filter
            if location:
                query += " AND js.location ILIKE %s"
                params.append(f"%{location}%")
            
            # Add education filter
            if education:
                query += " AND js.education ILIKE %s"
                params.append(f"%{education}%")
            
            # Add limit
            query += " LIMIT %s"
            params.append(limit)
            
            # We already created a cursor above, so we don't need to create it again
            # cursor = conn.cursor()
            cursor.execute(query, params)
            
            seekers = []
            for row in cursor.fetchall():
                seekers.append(JobSeeker(
                    id=row[0],
                    user_id=row[1],
                    full_name=row[2],
                    bio=row[3],
                    skills=row[4],
                    experience=row[5],
                    education=row[6],
                    location=row[7],
                    credits=row[8],
                    profile_complete=True
                ))
            
            return seekers
        except psycopg2.Error as e:
            print(f"Error getting job seekers for swiping: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def add_credits(self, amount):
        """Add credits to job seeker account"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE job_seekers
                SET credits = credits + %s
                WHERE user_id = %s
                RETURNING credits
                """,
                (amount, self.user_id)
            )
            
            new_credits = cursor.fetchone()[0]
            conn.commit()
            self.credits = new_credits
            
            # Record the transaction
            cursor.execute(
                """
                INSERT INTO credit_transactions 
                (user_id, amount, transaction_type, description)
                VALUES (%s, %s, %s, %s)
                """,
                (self.user_id, amount, 'credit', 'Match credit')
            )
            
            conn.commit()
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error adding credits to job seeker: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def redeem_credits(self, amount_to_redeem: int = 100, upi_id: str = None, whatsapp_number: str = None):
        """
        Redeem credits if balance is sufficient for the amount_to_redeem.
        
        Args:
            amount_to_redeem: Amount of credits to redeem
            upi_id: UPI ID for payment
            whatsapp_number: WhatsApp number for contact
        """
        # If UPI ID and WhatsApp number are provided, create a redemption request
        if upi_id and whatsapp_number:
            return self.create_redemption_request(amount_to_redeem, upi_id, whatsapp_number)
        
        # Otherwise, just check if we have enough credits (for validation)
        if self.credits < amount_to_redeem:
            return False, f"Insufficient credits. You need at least {amount_to_redeem} credits to redeem."
        
        return True, "Please provide your UPI ID and WhatsApp number to complete the redemption."
    
    def create_redemption_request(self, amount_to_redeem: int, upi_id: str, whatsapp_number: str):
        """
        Create a redemption request with UPI ID and WhatsApp number.
        
        Args:
            amount_to_redeem: Amount of credits to redeem
            upi_id: UPI ID for payment
            whatsapp_number: WhatsApp number for contact
        """
        if self.credits < amount_to_redeem:
            return False, f"Insufficient credits. You need at least {amount_to_redeem} credits to redeem."
        
        conn = get_connection()
        if conn is None:
            return False, "Database connection error"
        
        try:
            cursor = conn.cursor()
            
            # First, update the job seeker's credits
            cursor.execute(
                """
                UPDATE job_seekers
                SET credits = credits - %s
                WHERE user_id = %s AND credits >= %s
                RETURNING credits
                """,
                (amount_to_redeem, self.user_id, amount_to_redeem)
            )
            
            result = cursor.fetchone()
            if not result:
                conn.rollback()
                return False, "Failed to redeem credits"
            
            new_credits = result[0]
            
            # Record the transaction
            cursor.execute(
                """
                INSERT INTO credit_transactions 
                (user_id, amount, transaction_type, description)
                VALUES (%s, %s, %s, %s)
                """,
                (self.user_id, -amount_to_redeem, 'redemption', f'{amount_to_redeem} Credits redemption')
            )
            
            # Create the redemption request
            cursor.execute(
                """
                INSERT INTO redemption_requests
                (user_id, job_seeker_id, amount, upi_id, whatsapp_number)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (self.user_id, self.id, amount_to_redeem, upi_id, whatsapp_number)
            )
            
            request_id = cursor.fetchone()[0]
            
            conn.commit()
            self.credits = new_credits
            
            # Try to send email notification to admin
            try:
                # Get admin email
                cursor.execute(
                    """
                    SELECT email FROM users WHERE user_type = 'admin' LIMIT 1
                    """
                )
                admin_email_result = cursor.fetchone()
                
                if admin_email_result:
                    admin_email = admin_email_result[0]
                    # In a real implementation, you would send an email here
                    print(f"Would send email to admin at {admin_email} about redemption request {request_id}")
            except Exception as email_error:
                print(f"Error sending admin notification: {email_error}")
                # Don't fail the transaction if email fails
            
            return True, f"Successfully submitted redemption request for {amount_to_redeem} credits! We'll process your request soon."
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error redeeming credits: {e}")
            return False, f"Error: {str(e)}"
        finally:
            cursor.close()
            conn.close()