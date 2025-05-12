import stripe
import os
from app.database.connection import get_connection
from datetime import datetime

# Initialize Stripe with your secret key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class Payment:
    @staticmethod
    def create_payment_intent(amount, currency='inr', user_id=None, package_id=None):
        """Create a Stripe PaymentIntent"""
        try:
            # Create a PaymentIntent with the order amount and currency
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents/paisa
                currency=currency,
                metadata={
                    'user_id': user_id,
                    'package_id': package_id
                }
            )
            return intent
        except Exception as e:
            print(f"Error creating payment intent: {e}")
            return None

    @staticmethod
    def record_payment(user_id, stripe_payment_id, amount, currency, status, package_id):
        """Record payment transaction in database"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO payment_transactions 
                (user_id, stripe_payment_id, amount, currency, status, package_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, stripe_payment_id, amount, currency, status, package_id))
            
            payment_id = cursor.fetchone()[0]
            conn.commit()
            return payment_id
        except Exception as e:
            conn.rollback()
            print(f"Error recording payment: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def handle_successful_payment(payment_intent_id):
        """Handle successful payment and add credits to user"""
        conn = get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Get payment details
            cursor.execute("""
                SELECT user_id, package_id, amount
                FROM payment_transactions
                WHERE stripe_payment_id = %s
            """, (payment_intent_id,))
            
            payment = cursor.fetchone()
            if not payment:
                return False
            
            user_id, package_id, amount = payment
            
            # Get package details
            cursor.execute("""
                SELECT credits_amount
                FROM credit_packages
                WHERE id = %s
            """, (package_id,))
            
            package = cursor.fetchone()
            if not package:
                return False
            
            credits_amount = package[0]
            
            # Get user type
            cursor.execute("""
                SELECT user_type
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                return False
            
            user_type = user[0]
            
            # Add credits based on user type
            if user_type == 'job_giver':
                cursor.execute("""
                    UPDATE job_givers
                    SET credits = credits + %s
                    WHERE user_id = %s
                """, (credits_amount, user_id))
            else:  # job_seeker
                cursor.execute("""
                    UPDATE job_seekers
                    SET credits = credits + %s
                    WHERE user_id = %s
                """, (credits_amount, user_id))
            
            # Record credit transaction
            cursor.execute("""
                INSERT INTO credit_transactions 
                (user_id, amount, transaction_type, description)
                VALUES (%s, %s, %s, %s)
            """, (user_id, credits_amount, 'purchase', f'Purchased {credits_amount} credits'))
            
            # Update payment status
            cursor.execute("""
                UPDATE payment_transactions
                SET status = 'completed'
                WHERE stripe_payment_id = %s
            """, (payment_intent_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"Error handling successful payment: {e}")
            return False
        finally:
            cursor.close()
            conn.close() 