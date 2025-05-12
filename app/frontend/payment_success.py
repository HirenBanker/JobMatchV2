import streamlit as st
import stripe
import os
from app.models.payment import Payment
from app.models.job_giver import JobGiver
from app.models.credit_package import CreditPackage
from app.database.connection import get_connection

def payment_success_page():
    st.title("Payment Status")
    
    # Get session ID from URL parameters
    session_id = st.experimental_get_query_params().get("session_id", [None])[0]
    
    if not session_id:
        st.error("Invalid payment session. Please try again.")
        st.button("Return to Credits", on_click=lambda: st.switch_page("credits"))
        return
    
    try:
        # Retrieve the checkout session
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            # Get metadata from session
            user_id = session.metadata.get('user_id')
            package_id = session.metadata.get('package_id')
            credits_amount = int(session.metadata.get('credits_amount'))
            
            # Update payment record
            payment = Payment.get_by_stripe_payment_id(session_id)
            if payment:
                payment.update_status('completed')
                
                # Add credits to user's account
                conn = get_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        # Add credits to job giver
                        cursor.execute("""
                            UPDATE job_givers
                            SET credits = credits + %s
                            WHERE user_id = %s
                        """, (credits_amount, user_id))
                        
                        # Record transaction
                        cursor.execute("""
                            INSERT INTO credit_transactions 
                            (user_id, amount, transaction_type, description)
                            VALUES (%s, %s, %s, %s)
                        """, (user_id, credits_amount, 'purchase', f'Purchased {credits_amount} credits'))
                        
                        conn.commit()
                        st.success(f"Payment successful! {credits_amount} credits have been added to your account.")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error adding credits: {e}")
                    finally:
                        cursor.close()
                        conn.close()
            else:
                st.error("Payment record not found. Please contact support.")
        else:
            st.error("Payment not completed. Please try again.")
            
    except Exception as e:
        st.error(f"Error processing payment: {e}")
    
    # Add button to return to credits page
    st.button("Return to Credits", on_click=lambda: st.switch_page("credits")) 