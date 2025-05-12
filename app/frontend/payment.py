import streamlit as st
import stripe
import os
from app.models.payment import Payment
from app.models.credit_package import CreditPackage

def show_payment_page():
    """Show payment page for purchasing credits"""
    st.title("Purchase Credits")
    
    # Get available credit packages
    packages = CreditPackage.get_all()
    if not packages:
        st.error("No credit packages available")
        return
    
    # Display packages
    st.write("### Available Credit Packages")
    for package in packages:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{package.name}**")
                if package.description:
                    st.write(package.description)
            with col2:
                st.write(f"**{package.credits_amount} Credits**")
            with col3:
                st.write(f"**₹{package.price_inr:.2f}**")
                if st.button("Purchase", key=f"buy_{package.id}"):
                    handle_purchase(package)

def handle_purchase(package):
    """Handle credit package purchase"""
    if not st.session_state.get('logged_in'):
        st.error("Please log in to purchase credits")
        return
    
    # Create payment intent
    intent = Payment.create_payment_intent(
        amount=package.price_inr,
        user_id=st.session_state.user_id,
        package_id=package.id
    )
    
    if not intent:
        st.error("Error creating payment. Please try again.")
        return
    
    # Record payment attempt
    payment_id = Payment.record_payment(
        user_id=st.session_state.user_id,
        stripe_payment_id=intent.id,
        amount=package.price_inr,
        currency='inr',
        status='pending',
        package_id=package.id
    )
    
    if not payment_id:
        st.error("Error recording payment. Please try again.")
        return
    
    # Show payment form
    st.write("### Complete Your Purchase")
    
    # Add Stripe Elements
    st.markdown(f"""
        <script src="https://js.stripe.com/v3/"></script>
        <script>
            const stripe = Stripe('{os.getenv('STRIPE_PUBLISHABLE_KEY')}');
            const elements = stripe.elements();
            
            // Create card element
            const card = elements.create('card');
            card.mount('#card-element');
            
            // Handle form submission
            const form = document.getElementById('payment-form');
            form.addEventListener('submit', async (event) => {{
                event.preventDefault();
                
                const {{paymentIntent, error}} = await stripe.confirmCardPayment(
                    '{intent.client_secret}',
                    {{
                        payment_method: {{
                            card: card,
                        }}
                    }}
                );
                
                if (error) {{
                    // Handle error
                    const errorElement = document.getElementById('card-errors');
                    errorElement.textContent = error.message;
                }} else {{
                    // Payment successful
                    window.location.href = '/payment_success?payment_intent=' + paymentIntent.id;
                }}
            }});
        </script>
        
        <form id="payment-form">
            <div id="card-element"></div>
            <div id="card-errors" role="alert"></div>
            <button type="submit">Pay ₹{package.price_inr:.2f}</button>
        </form>
    """, unsafe_allow_html=True)

def handle_payment_success():
    """Handle successful payment"""
    payment_intent_id = st.query_params.get('payment_intent', [None])[0]
    if not payment_intent_id:
        st.error("Invalid payment")
        return
    
    # Handle successful payment
    if Payment.handle_successful_payment(payment_intent_id):
        st.success("Payment successful! Your credits have been added to your account.")
        st.balloons()
    else:
        st.error("Error processing payment. Please contact support.") 