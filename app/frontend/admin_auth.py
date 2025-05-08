import streamlit as st
from app.models.user import User
from app.database.connection import get_connection

def admin_login_page():
    """Admin login page"""
    st.title("JobMatch Administration")
    
    # Add some styling and information
    st.markdown("""
    <style>
    .admin-header {
        color: #1E3A8A;
        font-size: 24px;
    }
    .admin-note {
        font-size: 14px;
        color: #666;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="admin-header">Secure Administration Portal</p>', unsafe_allow_html=True)
    
    # Check if admin exists
    admin_exists = check_admin_exists()
    
    # Show security note
    with st.expander("Security Information", expanded=False):
        st.markdown("""
        This is a secure administration area. Unauthorized access attempts are logged and monitored.
        
        **Access Methods:**
        - Press **Ctrl+Alt+A** on any page to access this portal
        - Add the admin access parameter to the URL
        - Click the hidden access point in the application
        
        If you've reached this page by accident, please return to the main application.
        """)
    
    if not admin_exists:
        st.warning("⚠️ No administrator account detected in the database. Initial setup required.")
        
        # Create admin form
        with st.form("create_admin_form"):
            st.subheader("Create Administrator Account")
            
            col1, col2 = st.columns(2)
            with col1:
                admin_username = st.text_input("Username", value="admin")
                admin_email = st.text_input("Email", value="admin@jobmatch.com")
            
            with col2:
                admin_password = st.text_input("Password", type="password", value="admin123")
                confirm_password = st.text_input("Confirm Password", type="password", value="admin123")
            
            st.markdown('<p class="admin-note">Note: Please use a strong password for production environments.</p>', unsafe_allow_html=True)
            
            create_button = st.form_submit_button("Create Administrator Account")
            
            if create_button:
                if not admin_username or not admin_email or not admin_password:
                    st.error("Please fill in all fields")
                elif admin_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(admin_password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    with st.spinner("Creating administrator account..."):
                        success, message = create_admin_user(admin_username, admin_email, admin_password)
                        if success:
                            st.success(f"✅ {message}")
                            st.info(f"""
                            **Administrator account created successfully!**
                            
                            Username: `{admin_username}`  
                            Email: `{admin_email}`
                            
                            You can now log in with these credentials.
                            """)
                            st.session_state.admin_created = True
                            # Don't rerun immediately to allow the user to see the success message
                        else:
                            st.error(f"❌ {message}")
    else:
        st.info("Please enter your administrator credentials to access the control panel.")
    
    # Login form
    with st.form("admin_login_form"):
        st.subheader("Administrator Login")
        
        username = st.text_input("Username", value="admin" if not admin_exists and st.session_state.get('admin_created') else "")
        password = st.text_input("Password", type="password", value="" if not st.session_state.get('admin_created') else "")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown('<p class="admin-note">Secure access to JobMatch administration features</p>', unsafe_allow_html=True)
        with col2:
            submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if not username or not password:
                st.error("Please enter both username and password")
                return
            
            # In demo mode, allow login with admin/admin
            if not st.session_state.db_connected and username == "admin" and password == "admin":
                st.session_state.logged_in = True
                st.session_state.user_id = 1
                st.session_state.username = "admin"
                st.session_state.user_type = "admin"
                st.success("Admin login successful (Demo Mode)!")
                st.rerun()
                return
            
            # Check if user exists and is an admin
            with st.spinner("Authenticating..."):
                user = User.authenticate(username, password)
                if user and user.user_type == "admin":
                    st.session_state.logged_in = True
                    st.session_state.user_id = user.id
                    st.session_state.username = user.username
                    st.session_state.user_type = "admin"
                    st.success("✅ Authentication successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials or insufficient privileges")
    
    # Back to main application button
    st.markdown("---")
    if st.button("← Return to Main Application"):
        st.session_state.admin_login = False
        st.rerun()
    
    # This section is no longer needed as we've added the back button in the main function
    pass

def check_admin_exists():
    """Check if admin user exists in the database"""
    conn = get_connection()
    if conn is None:
        print("Warning: Could not check if admin exists - database connection failed")
        # In case of connection error, assume no admin exists to allow creation
        return False
    
    try:
        cursor = conn.cursor()
        # First check if the users table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = 'users'
            )
        """)
        
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("Users table does not exist yet")
            return False
            
        # If table exists, check for admin users
        cursor.execute("""
            SELECT COUNT(*) FROM users WHERE user_type = 'admin'
        """)
        
        count = cursor.fetchone()[0]
        admin_exists = count > 0
        print(f"Admin check: Found {count} admin users")
        return admin_exists
    except Exception as e:
        print(f"Error checking admin existence: {e}")
        # In case of error, assume no admin exists to allow creation
        return False
    finally:
        if conn:
            if 'cursor' in locals() and cursor:
                try:
                    cursor.close()
                except:
                    pass
            try:
                conn.close()
            except:
                pass

def create_admin_user(username, email, password):
    """Create a new admin user"""
    import time
    
    # Check if admin already exists
    if check_admin_exists():
        return False, "Administrator account already exists"
    
    # Check database connection
    conn = get_connection()
    if conn is None:
        print("Failed to create admin: Database connection error")
        return False, "Database connection error. Please check your connection settings."
    
    try:
        conn.close()  # Just testing connection, close it right away
    except Exception:
        pass
    
    # Add a small delay to simulate processing (improves UX)
    time.sleep(0.5)
    
    # Create admin user
    try:
        user = User.create(username, email, password, "admin")
        if user:
            print(f"Administrator account created successfully: {username}")
            return True, "Administrator account created successfully"
        else:
            print(f"Failed to create administrator account: {username}")
            return False, "Failed to create administrator account. Check database connection."
    except Exception as e:
        print(f"Exception creating admin user: {str(e)}")
        return False, f"Error creating administrator account: {str(e)}"