import streamlit as st
from app.frontend.admin import admin_dashboard
from app.frontend.admin_auth import admin_login_page
from app.frontend.job_seeker import job_seeker_dashboard
from app.frontend.job_giver import job_giver_dashboard
from app.database.connection import init_db
from app.frontend.auth import handle_auth_flow
# Initialize the database
db_connected = init_db()

# Set a flag in session state to indicate if we're in demo mode
# This needs to be done BEFORE any page tries to access it.
if "db_connected" not in st.session_state:
    st.session_state.db_connected = db_connected
elif not hasattr(st.session_state, 'db_connected'): # Defensive check
    st.session_state.db_connected = db_connected

# Set page config
st.set_page_config(
    page_title="JobMatch - Easily Match Jobs",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add JavaScript for hidden admin access (Ctrl+Alt+A)
st.markdown("""
<script>
document.addEventListener('keydown', function(e) {
    // Check for Ctrl+Alt+A
    if (e.ctrlKey && e.altKey && e.key === 'a') {
        // Set URL parameter for admin access
        const url = new URL(window.location.href);
        url.searchParams.set('admin_access', 'jobmatch_admin_2024');
        window.location.href = url.toString();
    }
});
</script>
""", unsafe_allow_html=True)

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_type" not in st.session_state:
    st.session_state.user_type = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

# Check for admin access via URL parameter
params = st.query_params
if "admin_access" in params and params["admin_access"][0] == "jobmatch_admin_2024":
    st.session_state.admin_login = True
    # If admin_login is true via URL, and they are not logged in as admin, force logout/re-auth
    if st.session_state.admin_login and \
       not (st.session_state.get('logged_in') and st.session_state.get('user_type') == 'admin'):
        st.session_state.logged_in = False # Force re-login for admin
        st.session_state.user_type = None  # Clear user type

# Main application flow
if not st.session_state.get('logged_in', False):
    # User is NOT logged in
    if st.session_state.get('admin_login', False):
        admin_login_page()  # Show admin login page if admin_login flag is set
    else:
        # Regular user authentication flow
        st.title("JobMatch - Find Your Perfect Fit")

        tab1, tab2, tab3 = st.tabs(["Login / Register", "About Us", "Contact Us"])

        with tab1:
            handle_auth_flow()  # Existing authentication flow

        with tab2:
            st.header("About JobMatch")
            st.markdown("""
            Welcome to JobMatch, the revolutionary platform designed to connect talented individuals 
            with their dream jobs and help recruiters find the perfect candidates efficiently.
            Our mission is to streamline the hiring process through an intuitive and engaging experience.
            """)
            
            st.subheader("How It Works")
            st.markdown("""
            - **Job Seekers:** Create catchy profiles - 80/20 rule: 80% about core work experience, 20% ancilliary experience
            - **Recruiters:** Create pointy job profiles - 80/20 rule : 80% about routine work, 20% about learning and growth the role offers
            - **Mutual Interest:** When both a job seeker and a recruiter express interest (swipe right), it's a match!
            - **Connect:** Matched parties can view full profiles and contact information to take the next steps.
            - **Credit System:** Recruiters use credits for actions like posting jobs and viewing full match details. Job seekers earn credits upon successful matches, which can be redeemed.
            """)
            
            st.markdown("---")
            
            col1_about, col2_about = st.columns(2)
            with col1_about:
                # You can replace these placeholders with actual image paths or URLs
                st.image("assets/images/our_vision.png", caption="Our Vision")
                st.subheader("Our Vision")
                st.markdown("""
                To be the leading job matching platform, recognized for innovation, user satisfaction, 
                and fostering successful career connections. We envision a world where finding the right 
                job or the right talent is a seamless and enjoyable journey.
                """)

            with col2_about:
                st.image("assets/images/our_technology.png", caption="Our Technology")
                st.subheader("Our Technology")
                st.markdown("""
                JobMatch leverages modern technology to provide a smart, fast, and reliable experience. 
                Our intuitive swipe interface makes job hunting and recruitment engaging and efficient.
                """)

        with tab3:
            st.header("Contact Us")
            st.image("assets/images/Contact_us.png", caption="We're here to help!")
            st.subheader("Get in Touch")
            st.markdown("""
            We value your feedback and are here to assist you with any inquiries.
            
            **Phone:**  
            📞 +91 76006 30594
            
            **Email:**  
            📧 support@jobmatch.com
            
            **Office Hours:**  
            Monday - Friday: 9:00 AM - 6:00 PM (IST)
            """)
            
            # Hidden admin access via footer
            st.markdown("""
            <div style="position: fixed; bottom: 5px; right: 5px; width: 20px; height: 20px; cursor: default;">
                <a href="?admin_access=jobmatch_admin_2024" style="display: block; width: 100%; height: 100%; text-decoration: none; color: transparent;">.</a>
            </div>
            """, unsafe_allow_html=True)
            
            # Add a small note about admin access methods (only visible in development)
            if st.session_state.db_connected == False:  # Only show in development/demo mode
                with st.expander("Developer Notes (Hidden in Production)", expanded=False):
                    st.markdown("""
                    **Admin Access Methods:**
                    1. Press **Ctrl+Alt+A** on any page
                    2. Click the invisible dot in the bottom-right corner of the page
                    3. Add `?admin_access=jobmatch_admin_2024` to the URL
                    """)
            
else:
    # User IS logged in
    # Show warning if database is not connected
    if not st.session_state.db_connected:
        st.warning("""
        **Database Connection Failed**
        
        The application is running in demo mode with limited functionality.
        To use all features, please ensure PostgreSQL is installed and running,
        and update the connection details in the .env file.
        """)

    # Sidebar for navigation when logged in
    with st.sidebar:
        st.title(f"Welcome, {st.session_state.username}")
        st.write(f"User Type: {st.session_state.user_type.replace('_', ' ').title()}") # Nicer display
        
        if st.button("Logout"):
            # Clear all session state keys upon logout
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Rerun to refresh the page to the login state
            st.rerun()

    # Route to appropriate dashboard based on user type
    if st.session_state.user_type == "admin":
        admin_dashboard()
    elif st.session_state.user_type == "job_seeker":
        job_seeker_dashboard()
    elif st.session_state.user_type == "job_giver":
        job_giver_dashboard()