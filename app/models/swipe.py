import psycopg2
from app.database.connection import get_connection
from app.models.job_seeker import JobSeeker
from app.models.job_giver import JobGiver

class Swipe:
    def __init__(self, id=None, user_id=None, target_id=None, target_type=None, 
                 direction=None, created_at=None, job_id=None):
        self.id = id
        self.user_id = user_id
        self.target_id = target_id
        self.target_type = target_type  # 'job' or 'job_seeker'
        self.direction = direction  # 'right' or 'left'
        self.created_at = created_at
        self.job_id = job_id  # Used when a job giver swipes on a job seeker for a specific job
    
    def create(self):
        """Create a new swipe record"""
        conn = get_connection()
        if conn is None:
            return False, "Database connection error"
        
        try:
            # Print debug info
            print(f"Creating swipe: user_id={self.user_id}, target_id={self.target_id}, target_type={self.target_type}, direction={self.direction}, job_id={self.job_id}")
            
            cursor = conn.cursor()
            
            # First, check if the job_id column exists in the swipes table
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='swipes' AND column_name='job_id'
            """)
            
            job_id_column_exists = cursor.fetchone() is not None
            
            # If the column doesn't exist, add it
            if not job_id_column_exists:
                cursor.execute("""
                    ALTER TABLE swipes 
                    ADD COLUMN job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE
                """)
                conn.commit()
                print("Added job_id column to swipes table")
            
            # Now insert the swipe with job_id if the column exists
            if job_id_column_exists:
                cursor.execute(
                    """
                    INSERT INTO swipes (user_id, target_id, target_type, direction, job_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (self.user_id, self.target_id, self.target_type, self.direction, self.job_id)
                )
            else:
                # Fall back to the original query without job_id
                cursor.execute(
                    """
                    INSERT INTO swipes (user_id, target_id, target_type, direction)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, created_at
                    """,
                    (self.user_id, self.target_id, self.target_type, self.direction)
                )
            
            swipe_id, created_at = cursor.fetchone()
            conn.commit()
            
            self.id = swipe_id
            self.created_at = created_at
            
            print(f"Swipe created with ID: {swipe_id}")
            
            # Check for match if swiped right
            if self.direction == 'right':
                print("Checking for match...")
                is_match, match_data = self.check_for_match()
                if is_match: # True if a new match created or if match already existed
                    if isinstance(match_data, dict): # New match created
                        print(f"New match created! Data: {match_data}")
                        return True, "It's a match!"
                    elif isinstance(match_data, str): # e.g., "Match already exists"
                        print(f"Match status: {match_data}")
                        return True, match_data 
                elif not is_match and match_data: # Match attempt failed, match_data contains error
                    print(f"Match attempt failed: {match_data}")
                    return False, str(match_data)
                # else: No match found, and no error during attempt (is_match is False, match_data is None)
                
                print("No match found or swipe was not a 'right' swipe leading to immediate match.")
            
            return True, "Swipe recorded"
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error creating swipe: {e}")
            return False, f"Error: {str(e)}"
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def reset_left_swipes(user_id, target_type='job_seeker', job_id=None):
        """
        Reset left swipes for a user on a specific target type
        This allows users to see candidates they previously swiped left on
        
        Args:
            user_id: The ID of the user who made the swipes
            target_type: The type of target ('job_seeker' or 'job')
            job_id: Optional specific job ID to reset swipes for
        
        Returns:
            tuple: (success, message)
        """
        conn = get_connection()
        if conn is None:
            return False, "Database connection error"
        
        try:
            cursor = conn.cursor()
            
            # First, check if the job_id column exists in the swipes table
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='swipes' AND column_name='job_id'
            """)
            
            job_id_column_exists = cursor.fetchone() is not None
            
            # Only delete left swipes that haven't resulted in matches
            if target_type == 'job_seeker':
                # For job givers swiping on job seekers
                if job_id and job_id_column_exists:
                    # Only reset swipes for a specific job
                    print(f"Resetting left swipes for job ID: {job_id}")
                    cursor.execute("""
                        DELETE FROM swipes
                        WHERE user_id = %s
                        AND target_type = %s
                        AND direction = 'left'
                        AND job_id = %s
                        AND target_id::integer NOT IN (
                            SELECT js.id
                            FROM matches m
                            JOIN job_seekers js ON m.job_seeker_id = js.id
                            JOIN job_givers jg ON m.job_giver_id = jg.id
                            WHERE jg.user_id = %s
                            AND m.job_id = %s
                        )
                    """, (user_id, target_type, job_id, user_id, job_id))
                else:
                    # Reset all swipes
                    print("Resetting all left swipes")
                    cursor.execute("""
                        DELETE FROM swipes
                        WHERE user_id = %s
                        AND target_type = %s
                        AND direction = 'left'
                        AND target_id::integer NOT IN (
                            SELECT js.id
                            FROM matches m
                            JOIN job_seekers js ON m.job_seeker_id = js.id
                            JOIN job_givers jg ON m.job_giver_id = jg.id
                            WHERE jg.user_id = %s
                        )
                    """, (user_id, target_type, user_id))
            else:
                # For job seekers swiping on jobs
                cursor.execute("""
                    DELETE FROM swipes
                    WHERE user_id = %s
                    AND target_type = %s
                    AND direction = 'left'
                    AND target_id::integer NOT IN (
                        SELECT j.id
                        FROM matches m
                        JOIN jobs j ON m.job_id = j.id
                        JOIN job_seekers js ON m.job_seeker_id = js.id
                        WHERE js.user_id = %s
                    )
                """, (user_id, target_type, user_id))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            return True, f"Reset {deleted_count} left swipes"
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error resetting swipes: {e}")
            return False, f"Error: {str(e)}"
        finally:
            cursor.close()
            conn.close()
    
    def check_for_match(self):
        """Check if this swipe creates a match"""
        conn = get_connection()
        if conn is None:
            return False, None
        
        try:
            cursor = conn.cursor()
            
            # Different logic based on who is swiping
            if self.target_type == 'job':
                # Job seeker swiped right on a job
                # First, get the job seeker's ID
                cursor.execute(
                    """
                    SELECT id FROM job_seekers WHERE user_id = %s
                    """,
                    (self.user_id,)
                )
                job_seeker_id_result = cursor.fetchone()
                if not job_seeker_id_result:
                    return False, None
                
                job_seeker_id = job_seeker_id_result[0]
                
                # Get job and job giver info
                cursor.execute(
                    """
                    SELECT j.id, j.job_giver_id, jg.user_id
                    FROM jobs j
                    JOIN job_givers jg ON j.job_giver_id = jg.id
                    WHERE j.id = %s
                    """,
                    (self.target_id,)
                )
                
                job_info = cursor.fetchone()
                if not job_info:
                    return False, None
                
                job_id, job_giver_id, job_giver_user_id = job_info
                
                # Check if job giver has swiped right on this job seeker FOR THIS SPECIFIC JOB
                cursor.execute(
                    """
                    SELECT 1
                    FROM swipes
                    WHERE user_id = %s          -- job_giver_user_id
                    AND target_id = %s          -- job_seeker_id
                    AND target_type = 'job_seeker'
                    AND direction = 'right'
                    AND job_id = %s;            -- The specific job_id the seeker swiped on
                    """,
                    (job_giver_user_id, job_seeker_id, job_id)
                )
                
                is_match = cursor.fetchone() is not None
                
                if is_match:
                    # Check if match already exists
                    cursor.execute(
                        """
                        SELECT 1 FROM matches
                        WHERE job_seeker_id = %s AND job_giver_id = %s AND job_id = %s
                        """,
                        (job_seeker_id, job_giver_id, job_id)
                    )
                    
                    match_exists = cursor.fetchone() is not None
                    
                    if not match_exists:
                        # Create match record
                        cursor.execute(
                            """
                            INSERT INTO matches (job_seeker_id, job_giver_id, job_id)
                            VALUES (%s, %s, %s)
                            RETURNING id
                            """,
                            (job_seeker_id, job_giver_id, job_id)
                        )
                        
                        match_id = cursor.fetchone()[0]
                        
                        # Transfer credits from job giver to job seeker
                        job_giver = JobGiver.get_by_user_id(job_giver_user_id)
                        credit_amount = 10  # New credit amount for matches
                        success, message = job_giver.use_credit(credit_amount)

                        if success:
                            job_seeker = JobSeeker.get_by_user_id(self.user_id)
                            if job_seeker.add_credits(credit_amount): # add_credits returns True/False
                                conn.commit()
                                return True, {
                                    'match_id': match_id,
                                    'job_id': job_id,
                                    'job_giver_id': job_giver_id,
                                    'job_seeker_id': job_seeker_id
                                }
                            else:
                                conn.rollback() # Rollback match if seeker credit fails
                                return False, "Failed to credit job seeker after match."
                        else:
                            conn.rollback() # Rollback match if giver credit use fails
                            return False, message # Propagate credit error message
                    else:
                        # Match already exists
                        conn.commit() # Commit as no change was made, but operation is "successful"
                        return True, "Match already exists"
            
            elif self.target_type == 'job_seeker':
                # Job giver swiped right on a job seeker
                # First, get the job giver's ID
                cursor.execute(
                    """
                    SELECT id FROM job_givers WHERE user_id = %s
                    """,
                    (self.user_id,)
                )
                job_giver_id_result = cursor.fetchone()
                if not job_giver_id_result:
                    return False, None
                
                job_giver_id = job_giver_id_result[0]
                
                # Get job seeker's user ID
                cursor.execute(
                    """
                    SELECT user_id FROM job_seekers WHERE id = %s
                    """,
                    (self.target_id,)
                )
                
                job_seeker_user_id_result = cursor.fetchone()
                if not job_seeker_user_id_result:
                    return False, None
                
                job_seeker_user_id = job_seeker_user_id_result[0]
                
                # Job giver swipe MUST be for a specific job to create a match
                if self.job_id:
                    # Check if the job seeker has swiped right on this specific job
                    cursor.execute(
                        """
                        SELECT 1
                        FROM swipes s
                        JOIN jobs j ON s.target_id = j.id
                        WHERE s.user_id = %s
                        AND s.target_type = 'job'
                        AND s.direction = 'right'
                        AND s.target_id = %s
                        AND j.job_giver_id = %s
                        """,
                        (job_seeker_user_id, self.job_id, job_giver_id)
                    )
                    
                    is_seeker_interested_in_this_job = cursor.fetchone() is not None
                    
                    if is_seeker_interested_in_this_job:
                        # Check if match already exists
                        cursor.execute(
                            """
                            SELECT 1 FROM matches
                            WHERE job_seeker_id = %s AND job_giver_id = %s AND job_id = %s
                            """,
                            (self.target_id, job_giver_id, self.job_id) # self.target_id is job_seeker.id
                        )
                        match_exists = cursor.fetchone() is not None

                        if not match_exists:
                            # Create match record for self.job_id
                            cursor.execute(
                                """
                                INSERT INTO matches (job_seeker_id, job_giver_id, job_id)
                                VALUES (%s, %s, %s)
                                RETURNING id
                                """,
                                (self.target_id, job_giver_id, self.job_id)
                            )
                            match_id = cursor.fetchone()[0]
                            
                            # Transfer credits
                            job_giver = JobGiver.get_by_user_id(self.user_id) # self.user_id is job_giver_user_id
                            credit_amount = 10 
                            success, message = job_giver.use_credit(credit_amount)

                            if success:
                                job_seeker = JobSeeker.get_by_user_id(job_seeker_user_id)
                                if job_seeker.add_credits(credit_amount):
                                    conn.commit()
                                    return True, {
                                        'match_id': match_id,
                                        'job_id': self.job_id,
                                        'job_giver_id': job_giver_id,
                                        'job_seeker_id': self.target_id
                                    }
                                else:
                                    conn.rollback()
                                    return False, "Failed to credit job seeker after match."
                            else:
                                conn.rollback()
                                return False, message # Propagate credit error
                        else: # Match already exists for this specific job
                            conn.commit()
                            return True, "Match already exists for this job"
                else: # self.job_id was not provided by job giver - no match under strict job-based matching
                    print("Job Giver swipe without specific job_id. No match created.")
                    # No commit needed as no changes made
                    return False, None
            
            conn.commit()
            return False, None
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error checking for match: {e}")
            return False, None
        finally:
            cursor.close()
            conn.close()