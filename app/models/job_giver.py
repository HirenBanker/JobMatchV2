import psycopg2
from app.database.connection import get_connection, release_connection

class JobGiver:
    def __init__(self, id=None, user_id=None, company_name=None, company_description=None, 
                 website=None, location=None, credits=0, profile_complete=False):
        self.id = id
        self.user_id = user_id
        self.company_name = company_name
        self.company_description = company_description
        self.website = website
        self.location = location
        self.credits = credits
        self.profile_complete = profile_complete
    
    @staticmethod
    def get_by_user_id(user_id):
        """Get a job giver by user ID with proper connection handling"""
        conn = None
        try:
            conn = get_connection()
            if not conn:
                print("Failed to get database connection")
                return None

            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, company_name, company_description, website, 
                       location, credits, profile_complete
                FROM job_givers
                WHERE user_id = %s
            """, (user_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return JobGiver(
                    id=result[0],
                    user_id=result[1],
                    company_name=result[2],
                    company_description=result[3],
                    website=result[4],
                    location=result[5],
                    credits=result[6],
                    profile_complete=result[7]
                )
            return None
        except Exception as e:
            print(f"Error getting job giver by user ID: {e}")
            return None
        finally:
            if conn:
                release_connection(conn)
    
    def update_profile(self):
        """Update job giver profile"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE job_givers
                SET company_name = %s, company_description = %s, website = %s, 
                    location = %s, profile_complete = %s
                WHERE user_id = %s
                RETURNING id
                """,
                (self.company_name, self.company_description, self.website, 
                 self.location, True, self.user_id)
            )
            
            updated_id = cursor.fetchone()[0]
            conn.commit()
            self.id = updated_id
            self.profile_complete = True
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error updating job giver profile: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def add_credits(self, amount):
        """Add credits to job giver account"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE job_givers
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
                (self.user_id, amount, 'purchase', 'Credit purchase')
            )
            
            conn.commit()
            return True
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error adding credits to job giver: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def use_credit(self, amount=10):
        """Use credits for a match"""
        if self.credits < amount:
            return False, f"Insufficient credits. You need {amount} credits for a match."
        
        conn = get_connection()
        if conn is None:
            return False, "Database connection error"
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE job_givers
                SET credits = credits - %s
                WHERE user_id = %s AND credits >= %s
                RETURNING credits
                """,
                (amount, self.user_id, amount)
            )
            
            result = cursor.fetchone()
            if not result:
                conn.rollback()
                return False, "Failed to use credit"
            
            new_credits = result[0]
            
            # Record the transaction
            cursor.execute(
                """
                INSERT INTO credit_transactions 
                (user_id, amount, transaction_type, description)
                VALUES (%s, %s, %s, %s)
                """,
                (self.user_id, -amount, 'match', f'{amount} credits used for match')
            )
            
            conn.commit()
            self.credits = new_credits
            return True, "Credit used successfully"
        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error using credit: {e}")
            return False, f"Error: {str(e)}"
        finally:
            cursor.close()
            conn.close()