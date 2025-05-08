import streamlit as st
from app.models.user import User
from app.database.connection import get_connection

def admin_login_page():
    """Admin login page"""
    st.title("Admin Login")
    
    # Add some styling and information
    st.markdown("""
    <style>
    .admin-header {
        color: #1E3A8A;
        font-size: 24px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="admin-header">JobMatch Administration</p>', unsafe_allow_html=True)
    st.write("Please enter your admin credentials to access the administration panel.")
    
    # Login form
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
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
            user = User.authenticate(username, password)
            if user and user.user_type == "admin":
                st.session_state.logged_in = True
                st.session_state.user_id = user.id
                st.session_state.username = user.username
                st.session_state.user_type = "admin"
                st.success("Admin login successful!")
                st.rerun()
            else:
                st.error("Invalid admin credentials")
    
    # Add a back to main login link
    if st.button("← Back to Main Login"):
        st.session_state.admin_login = False
        st.rerun()

def check_admin_exists():
    """Check if admin user exists in the database"""
    conn = get_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM users WHERE user_type = 'admin'
        """)
        
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"Error checking admin existence: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def create_admin_user(username, email, password):
    """Create a new admin user"""
    # Check if admin already exists
    if check_admin_exists():
        return False, "Admin user already exists"
    
    # Create admin user
    user = User.create(username, email, password, "admin")
    if user:
        return True, "Admin user created successfully"
    else:
        return False, "Failed to create admin user"