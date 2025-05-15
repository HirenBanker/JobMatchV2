import streamlit as st
from app.models.user import User
from app.database.connection import get_connection

def handle_auth_flow():
    """Manages and displays the current authentication view."""
    # Initialize session state for auth view management if they are missing.
    # This is important after a full session state clear (e.g., logout).
    if 'auth_view' not in st.session_state:
        # Possible views: 'login', 'register', 'forgot_password_step1', 'forgot_password_step2'
        st.session_state.auth_view = 'login'
    if 'username_for_reset' not in st.session_state:
        st.session_state.username_for_reset = None
        
    if st.session_state.auth_view == 'login':
        login_page()
    elif st.session_state.auth_view == 'register':
        register_page()
    elif st.session_state.auth_view == 'forgot_password_step1':
        forgot_password_step1_page()
    elif st.session_state.auth_view == 'forgot_password_step2':
        forgot_password_step2_page()

def login_page():
    """Login page for all user types"""
    st.header("Login to JobMatch")
    
    if not st.session_state.db_connected:
        st.info("Demo mode: Use username 'admin' and password 'admin' to login")
    
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    
    # Create two columns for login and forgot password buttons
    col1, col2 = st.columns([3, 2])

    with col1:
        if st.button("Login", key="login_button", use_container_width=True):
            if not username or not password:
                st.error("Please enter both username and password")
                return
            
            if not st.session_state.db_connected and username == "admin" and password == "admin":
                st.session_state.logged_in = True
                st.session_state.user_id = 1 # Demo user ID
                st.session_state.username = "admin"
                st.session_state.user_type = "admin"
                st.success("Login successful (Demo Mode)!")
                st.rerun()
                return
            
            auth_result = User.authenticate(username, password) 
            
            if isinstance(auth_result, User): # Successfully authenticated and active
                # Allow login for ANY user type if authentication is successful
                st.session_state.logged_in = True
                # Set session state with the actual user data returned by authenticate
                # This allows admins to log in via this page again
                st.session_state.user_id = auth_result.id
                st.session_state.username = auth_result.username
                st.session_state.user_type = auth_result.user_type
                st.success("Login successful!")
                st.rerun()
            elif auth_result == "suspended":
                # Account is suspended
                st.error("Your account has been suspended. Please contact support.")
            elif auth_result is None: # Invalid credentials or other auth error
                st.error("Invalid username or password.")
            else: # Should not happen, but as a fallback
                st.error("An unexpected error occurred during login. Please try again.")
    
    with col2:
        if st.button("Forgot Password?", key="forgot_password_button", use_container_width=True):
            st.session_state.auth_view = 'forgot_password_step1'
            st.rerun()

    st.markdown("---")
    st.write("Don't have an account?")
    if st.button("Register Here", key="go_to_register_button"):
        st.session_state.auth_view = 'register'
        st.rerun()

    # Add admin account creation section (hidden by default)
    if st.session_state.get('show_admin_creation', False):
        st.markdown("---")
        with st.expander("Admin Account Creation", expanded=True):
            st.write("Create an admin account")
            
            admin_username = st.text_input("Admin Username", key="admin_username")
            admin_email = st.text_input("Admin Email", key="admin_email")
            admin_password = st.text_input("Admin Password", type="password", key="admin_password")
            admin_confirm_password = st.text_input("Confirm Admin Password", type="password", key="admin_confirm_password")
            
            if st.button("Create Admin Account", key="create_admin_button"):
                if not admin_username or not admin_email or not admin_password:
                    st.error("Please fill in all fields")
                    return
                
                if admin_password != admin_confirm_password:
                    st.error("Passwords do not match")
                    return
                
                # Check if username already exists
                conn = get_connection()
                if conn is None:
                    st.error("Database connection failed")
                    return
                    
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM users WHERE username = %s", (admin_username,))
                    if cursor.fetchone():
                        st.error("Username already exists. Please choose a different username.")
                        return
                    
                    # Create admin account
                    user = User.create(admin_username, admin_email, admin_password, 'admin')
                    if user:
                        st.success("Admin account created successfully! You can now login.")
                        st.session_state.show_admin_creation = False  # Hide the section after successful creation
                        st.rerun()
                    else:
                        st.error("Failed to create admin account")
                except Exception as e:
                    st.error(f"Error creating admin account: {str(e)}")
                finally:
                    cursor.close()
                    conn.close()

    # Add JavaScript for admin creation access (Ctrl+Alt+A)
    st.markdown("""
    <script>
    document.addEventListener('keydown', function(e) {
        // Check for Ctrl+Alt+A
        if (e.ctrlKey && e.altKey && e.key === 'a') {
            // Toggle admin creation visibility
            const url = new URL(window.location.href);
            url.searchParams.set('show_admin_creation', 'true');
            window.location.href = url.toString();
        }
    });
    </script>
    """, unsafe_allow_html=True)

    # Check for admin creation access via URL parameter
    params = st.query_params
    if "show_admin_creation" in params and params["show_admin_creation"][0] == "true":
        st.session_state.show_admin_creation = True
        st.rerun()

def register_page():
    """Registration page for job seekers and job givers"""
    st.header("Register for JobMatch")
    
    if not st.session_state.db_connected:
        st.warning("Registration is not available in demo mode. Please connect to a database to register.")
        if st.button("← Back to Login", key="register_back_to_login_demo"):
            st.session_state.auth_view = 'login'
            st.rerun()
        return
    
    user_type = st.selectbox("I am a", ["Job Seeker", "Job Giver"], 
                             format_func=lambda x: "Candidate" if x == "Job Seeker" else "Recruiter",
                             key="register_user_type")
    
    username = st.text_input("Username (unique)", key="register_username")
    email = st.text_input("Email", key="register_email")
    password = st.text_input("Password", type="password", key="register_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password")
    
    if st.button("Register", key="register_button"):
        # Validate inputs
        if not username or not email or not password:
            st.error("Please fill in all fields")
            return
        
        if password != confirm_password:
            st.error("Passwords do not match")
            return
        
        # Check if username already exists
        existing_user = User.get_by_username(username)
        if existing_user:
            st.error("Username already exists. Please choose another one.")
            return
        
        # Create user
        user_type_value = "job_seeker" if user_type == "Job Seeker" else "job_giver"
        print(f"AUTH.PY: Attempting to register user: username='{username}', email='{email}', type='{user_type_value}'") # DEBUG
        user = User.create(username, email, password, user_type_value)
        
        if user:
            st.success("Registration successful! Please login.")
            print(f"AUTH.PY: Successfully registered user: {username}, ID: {user.id}") # DEBUG
            st.session_state.auth_view = 'login' # Redirect to login after successful registration
            st.rerun()
        else:
            # This block is hit if User.create returns None
            st.error("Registration failed. Please try again.")
            print(f"AUTH.PY: Registration failed for user: {username}. User.create returned: {user}") # DEBUG
            # The User.create method itself should print specific database errors.
            # This message confirms that the frontend received a None from User.create.

    st.markdown("---")
    if st.button("← Back to Login", key="register_back_to_login"):
        print("AUTH.PY: User clicked 'Back to Login' from register page.") # DEBUG
        st.session_state.auth_view = 'login'
        st.rerun()

def forgot_password_step1_page():
    """Step 1 of forgot password: User enters username and email."""
    st.header("Forgot Password - Step 1")
    st.write("Please enter your username and email to verify your account.")

    if not st.session_state.db_connected:
        st.warning("Password reset is not available in demo mode.")
        if st.button("← Back to Login", key="forgot_pw_s1_back_to_login_demo"):
            st.session_state.auth_view = 'login'
            st.rerun()
        return

    with st.form("forgot_password_step1_form"):
        username = st.text_input("Username", key="forgot_pw_s1_username")
        email = st.text_input("Email", key="forgot_pw_s1_email")
        
        submit_button = st.form_submit_button("Verify Account")

        if submit_button:
            if not username or not email:
                st.error("Please enter both username and email.")
            else:
                # Case-insensitive email check might be good, handled in User model
                user = User.get_by_username_and_email(username, email)
                if user:
                    st.session_state.username_for_reset = user.username
                    st.session_state.auth_view = 'forgot_password_step2'
                    st.success("Account verified. Please set your new password.") # This message might not show due to rerun
                    st.rerun()
                else:
                    st.error("Invalid username or email, or account not found.")
    
    st.markdown("---")
    if st.button("← Back to Login", key="forgot_pw_s1_back_to_login"):
        st.session_state.auth_view = 'login'
        st.rerun()

def forgot_password_step2_page():
    """Step 2 of forgot password: User sets a new password."""
    st.header("Forgot Password - Step 2")

    username_to_reset = st.session_state.get('username_for_reset')

    if not username_to_reset:
        st.error("No user specified for password reset. Please start over from Step 1.")
        if st.button("Go to Step 1", key="fp_s2_go_step1"):
            st.session_state.auth_view = 'forgot_password_step1'
            st.rerun()
        return

    st.write(f"Setting new password for user: **{username_to_reset}**")

    with st.form("forgot_password_step2_form"):
        new_password = st.text_input("New Password", type="password", key="forgot_pw_s2_new_password")
        confirm_new_password = st.text_input("Confirm New Password", type="password", key="forgot_pw_s2_confirm_password")
        
        submit_button = st.form_submit_button("Set New Password")

        if submit_button:
            if not new_password or not confirm_new_password:
                st.error("Please fill in both password fields.")
            elif new_password != confirm_new_password:
                st.error("Passwords do not match.")
            # Add password strength validation here if desired (e.g., min length)
            elif len(new_password) < 6: # Basic example: minimum 6 characters
                st.error("Password must be at least 6 characters long.")
            else:
                if User.update_password_by_username(username_to_reset, new_password):
                    st.session_state.username_for_reset = None # Clear the username
                    st.session_state.auth_view = 'login' # Prepare to go to login
                    st.success("Password updated successfully! You can now login with your new password.")
                    # To ensure the success message is seen before rerun, or use a button
                    # For now, let's add a small delay or rely on the button below.
                    # st.experimental_rerun() # or st.rerun() for newer versions
                    # A button is often better UX here.
                else:
                    st.error("Failed to update password. Please try again or contact support.")
    
    st.markdown("---")
    if st.button("← Back to Login", key="forgot_pw_s2_back_to_login"):
        st.session_state.username_for_reset = None # Clear session state
        st.session_state.auth_view = 'login'
        st.rerun()