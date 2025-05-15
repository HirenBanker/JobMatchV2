import streamlit as st
import pandas as pd
from app.database.connection import get_connection
from app.models.job_giver import JobGiver
from app.models.credit_package import CreditPackage # Import the new model
from app.models.user import User
from app.models.job import Job

def admin_dashboard():
    """Admin dashboard for managing the platform"""
    st.title("Admin Dashboard")
    
    # Sidebar menu
    admin_menu = st.sidebar.radio(
        "Admin Menu",
        ["Dashboard", "Manage Users", "Manage Jobs", "Credit Transactions", "Manage Credits", "Redemption Requests", "System Settings"],
        key="admin_menu"
    )
    
    if admin_menu == "Dashboard":
        show_admin_dashboard()
    elif admin_menu == "Manage Users":
        manage_users()
    elif admin_menu == "Manage Jobs":
        manage_jobs()
    elif admin_menu == "Credit Transactions":
        credit_transactions()
    elif admin_menu == "Manage Credits":
        manage_user_credits()
    elif admin_menu == "Redemption Requests":
        redemption_requests()
    elif admin_menu == "System Settings":
        system_settings()

def show_admin_dashboard():
    """Show admin dashboard with key metrics"""
    st.header("Platform Overview")
    
    # Get database connection
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get user counts
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE user_type = 'job_seeker') AS job_seekers,
                COUNT(*) FILTER (WHERE user_type = 'job_giver') AS job_givers
            FROM users
            WHERE user_type != 'admin'
        """)
        
        user_counts = cursor.fetchone()
        job_seekers_count, job_givers_count = user_counts
        
        # Get job counts
        cursor.execute("SELECT COUNT(*) FROM jobs")
        jobs_count = cursor.fetchone()[0]
        
        # Get match counts
        cursor.execute("SELECT COUNT(*) FROM matches")
        matches_count = cursor.fetchone()[0]
        
        # Get credit transaction sum
        cursor.execute("""
            SELECT 
                SUM(amount) FILTER (WHERE transaction_type = 'purchase') AS purchased,
                SUM(amount) FILTER (WHERE transaction_type = 'redemption') AS redeemed
            FROM credit_transactions
        """)
        
        credit_sums = cursor.fetchone()
        credits_purchased = credit_sums[0] or 0
        credits_redeemed = abs(credit_sums[1] or 0)
        
        # Get pending redemption requests count
        cursor.execute("""
            SELECT COUNT(*) FROM redemption_requests WHERE status = 'pending'
        """)
        pending_redemptions = cursor.fetchone()[0]
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Job Seekers", job_seekers_count)
        col2.metric("Job Givers", job_givers_count)
        col3.metric("Total Jobs", jobs_count)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Matches", matches_count)
        col2.metric("Credits Purchased", credits_purchased)
        col3.metric("Credits Redeemed", credits_redeemed)
        
        # Show pending redemption requests with a warning color if there are any
        if pending_redemptions > 0:
            st.warning(f"⚠️ **{pending_redemptions} Pending Redemption Requests** - [View Requests](/?admin_menu=Redemption%20Requests)")
            if st.button("Go to Redemption Requests"):
                st.session_state.admin_menu = "Redemption Requests"
                st.rerun()
        
        # Recent activity
        st.subheader("Recent Activity")
        
        # Recent registrations
        cursor.execute("""
            SELECT username, user_type, created_at
            FROM users
            WHERE user_type != 'admin'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        recent_users = cursor.fetchall()
        if recent_users:
            st.write("Recent Registrations:")
            user_df = pd.DataFrame(
                recent_users,
                columns=["Username", "User Type", "Registered At"]
            )
            user_df["User Type"] = user_df["User Type"].apply(
                lambda x: "Candidate" if x == "job_seeker" else "Recruiter"
            )
            st.dataframe(user_df)
        
        # Recent matches
        cursor.execute("""
            SELECT 
                m.created_at,
                js.full_name AS job_seeker,
                jg.company_name AS company,
                j.title AS job_title
            FROM matches m
            JOIN job_seekers js ON m.job_seeker_id = js.id
            JOIN job_givers jg ON m.job_giver_id = jg.id
            JOIN jobs j ON m.job_id = j.id
            ORDER BY m.created_at DESC
            LIMIT 5
        """)
        
        recent_matches = cursor.fetchall()
        if recent_matches:
            st.write("Recent Matches:")
            match_df = pd.DataFrame(
                recent_matches,
                columns=["Matched At", "Candidate", "Company", "Job Title"]
            )
            st.dataframe(match_df)
        
    except Exception as e:
        st.error(f"Error retrieving dashboard data: {e}")
    finally:
        cursor.close()
        conn.close()

def manage_users():
    """Manage users section"""
    st.header("Manage Users")

    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        user_type_filter = st.selectbox(
            "Filter by user type",
            ["All Users", "Job Seekers", "Job Givers"],
            key="user_type_filter"
        )

    # Fetch all users using the new method from your User model
    users = User.get_all_managed_users() # This should return a list of dicts
    current_admin_user_id = st.session_state.get("user_id")

    if not st.session_state.get("db_connected", True): # Check if DB is connected
        st.warning("Database not connected. User management is unavailable.")
        return # Stop further execution in this tab
        
    if not current_admin_user_id:
        st.error("Admin user ID not found in session. Please re-login.")
        return # Stop further execution in this tab

    if not users:
        st.info("No users found or unable to retrieve user list.")
        return # Stop further execution in this tab

    # Initialize selected_users in session state if it doesn't exist
    if 'selected_users' not in st.session_state:
        st.session_state.selected_users = []

    # Filter users based on selection
    filtered_users = users
    if user_type_filter == "Job Seekers":
        filtered_users = [user for user in users if user['user_type'] == 'job_seeker']
    elif user_type_filter == "Job Givers":
        filtered_users = [user for user in users if user['user_type'] == 'job_giver']

    # Create DataFrame for display
    if filtered_users:
        user_df = pd.DataFrame(
            filtered_users,
            columns=["id", "username", "email", "user_type", "is_active"]
        )
        
        # Rename columns for display
        user_df.columns = ["ID", "Username", "Email", "User Type", "Active"]
        
        # Format user type for better display
        user_df["User Type"] = user_df["User Type"].apply(
            lambda x: "Candidate" if x == "job_seeker" else "Recruiter"
        )
        
        # Format active status with checkmark or X
        user_df["Active"] = user_df["Active"].apply(lambda x: "✅" if x else "❌")
        
        # Add checkbox column for selection
        user_df["Select"] = user_df["ID"].apply(
            lambda id: str(id) in st.session_state.selected_users
        )
        
        # Reorder columns to put Select first
        user_df = user_df[["Select", "ID", "Username", "Email", "User Type", "Active"]]
        
        # Display as editable dataframe
        edited_df = st.data_editor(
            user_df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select users for bulk actions",
                ),
                "ID": st.column_config.NumberColumn(
                    "ID",
                    help="User ID",
                    disabled=True,
                ),
                "Username": st.column_config.TextColumn(
                    "Username",
                    help="User's username",
                    disabled=True,
                ),
                "Email": st.column_config.TextColumn(
                    "Email",
                    help="User's email",
                    disabled=True,
                ),
                "User Type": st.column_config.TextColumn(
                    "User Type",
                    help="Type of user",
                    disabled=True,
                ),
                "Active": st.column_config.TextColumn(
                    "Active",
                    help="Account status",
                    disabled=True,
                ),
            },
            hide_index=True,
            use_container_width=True,
        )
        
        # Update selected users based on dataframe
        selected_user_ids = edited_df[edited_df["Select"] == True]["ID"].astype(str).tolist()
        st.session_state.selected_users = selected_user_ids
        
        # Check if admin selected themselves
        admin_selected_self = str(current_admin_user_id) in selected_user_ids

        # User details section
        st.subheader("User Details")
        selected_user_id = st.number_input("Enter User ID to view details", min_value=1, step=1, key="selected_user_id")
        
        # Store the selected user ID in session state to persist across reruns
        if st.button("View User Details", key="view_user_details_button"):
            st.session_state.viewing_user_id = selected_user_id
            show_user_details(selected_user_id)
        
        # If we have a user ID in session state, show its details
        elif 'viewing_user_id' in st.session_state:
            show_user_details(st.session_state.viewing_user_id)
        
        # Add action buttons at the bottom if any users are selected
        if selected_user_ids:
            st.subheader("Bulk Actions")
            
            # Show how many users are selected
            st.write(f"Selected {len(selected_user_ids)} user(s)")
            
            if admin_selected_self:
                st.warning("⚠️ You have selected yourself. You cannot suspend or delete your own account.")
            
            # Create 3 columns for the action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Suspend Selected", type="secondary", use_container_width=True, 
                            disabled=admin_selected_self):
                    success_count = 0
                    for user_id in selected_user_ids:
                        # Skip if trying to suspend self
                        if str(user_id) == str(current_admin_user_id):
                            continue
                        
                        if User.set_active_status(user_id, False):
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"Successfully suspended {success_count} user(s).")
                        # Clear selection
                        st.session_state.selected_users = []
                        st.rerun()
                    else:
                        st.error("Failed to suspend any users.")
            
            with col2:
                if st.button("Reactivate Selected", type="primary", use_container_width=True):
                    success_count = 0
                    for user_id in selected_user_ids:
                        if User.set_active_status(user_id, True):
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"Successfully reactivated {success_count} user(s).")
                        # Clear selection
                        st.session_state.selected_users = []
                        st.rerun()
                    else:
                        st.error("Failed to reactivate any users.")
            
            with col3:
                if st.button("Delete Selected", type="primary", use_container_width=True, 
                            disabled=admin_selected_self):
                    # Set a session state variable to trigger confirmation
                    st.session_state.confirm_bulk_delete = True
                    st.rerun()
        
        # Confirmation dialog for bulk delete
        if st.session_state.get("confirm_bulk_delete"):
            selected_count = len(st.session_state.selected_users)
            
            st.warning(f"Are you sure you want to delete {selected_count} selected user(s)? This action cannot be undone and will remove all associated data.")
            
            # Use columns for button layout
            confirm_cols = st.columns(6)
            
            if confirm_cols[0].button("Yes, Delete Users", key="confirm_bulk_delete_yes", type="primary"):
                success_count = 0
                for user_id in st.session_state.selected_users:
                    # Skip if trying to delete self
                    if str(user_id) == str(current_admin_user_id):
                        continue
                    
                    success, message = User.delete_user_by_id(user_id, current_admin_user_id)
                    if success:
                        success_count += 1
                
                if success_count > 0:
                    st.success(f"Successfully deleted {success_count} user(s).")
                else:
                    st.error("Failed to delete any users.")
                
                # Clean up session state variables
                st.session_state.confirm_bulk_delete = False
                st.session_state.selected_users = []
                st.rerun()
            
            if confirm_cols[1].button("Cancel", key="confirm_bulk_delete_no"):
                st.session_state.confirm_bulk_delete = False
                st.rerun()
    else:
        st.info("No users found matching the filter criteria.")

    # Check for confirmation dialog that might have been triggered by individual delete buttons
    # This is kept for backward compatibility
    if st.session_state.get("confirm_delete_user_id"):
        user_id_to_delete = st.session_state.get("confirm_delete_user_id")
        username_to_delete = st.session_state.get("confirm_delete_username", "this user")
        
        st.warning(f"Are you sure you want to delete user '{username_to_delete}' (ID: {user_id_to_delete})? This action cannot be undone and will remove all associated data.")
        
        # Use columns for button layout if desired, or just place them sequentially
        confirm_cols = st.columns(6)
        
        if confirm_cols[0].button("Yes, Delete User", key=f"confirm_delete_yes_{user_id_to_delete}", type="primary"):
            success, message = User.delete_user_by_id(user_id_to_delete, current_admin_user_id)
            if success:
                st.success(message)
            else:
                st.error(message)
            # Clean up session state variables for confirmation
            del st.session_state["confirm_delete_user_id"]
            if "confirm_delete_username" in st.session_state:
                del st.session_state["confirm_delete_username"]
            st.rerun()
            
        if confirm_cols[1].button("Cancel", key=f"confirm_delete_no_{user_id_to_delete}"):
            # Clean up session state variables for confirmation
            del st.session_state["confirm_delete_user_id"]
            if "confirm_delete_username" in st.session_state:
                del st.session_state["confirm_delete_username"]
            st.rerun()

def show_user_details(user_id):
    """Show details for a specific user"""
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute("""
            SELECT id, username, email, user_type, created_at
            FROM users
            WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            st.error("User not found")
            return
        
        user_id, username, email, user_type, created_at = user
        
        st.write(f"**Username:** {username}")
        st.write(f"**Email:** {email}")
        st.write(f"**User Type:** {'Candidate' if user_type == 'job_seeker' else 'Recruiter'}")
        st.write(f"**Registered:** {created_at}")
        
        # Get additional profile info based on user type
        if user_type == 'job_seeker':
            cursor.execute("""
                SELECT full_name, bio, skills, experience, location, credits, profile_complete
                FROM job_seekers
                WHERE user_id = %s
            """, (user_id,))
            
            profile = cursor.fetchone()
            if profile:
                full_name, bio, skills, experience, location, credits, profile_complete = profile
                
                st.write(f"**Full Name:** {full_name or 'Not provided'}")
                st.write(f"**Location:** {location or 'Not provided'}")
                st.write(f"**Experience:** {experience or 'Not provided'} years")
                st.write(f"**Credits:** {credits}")
                st.write(f"**Profile Complete:** {'Yes' if profile_complete else 'No'}")
                
                if skills:
                    st.write("**Skills:**")
                    st.write(", ".join(skills))
                
                if bio:
                    st.write("**Bio:**")
                    st.write(bio)
        
        elif user_type == 'job_giver':
            cursor.execute("""
                SELECT company_name, company_description, website, location, credits, profile_complete
                FROM job_givers
                WHERE user_id = %s
            """, (user_id,))
            
            profile = cursor.fetchone()
            if profile:
                company_name, company_description, website, location, credits, profile_complete = profile
                
                st.write(f"**Company:** {company_name or 'Not provided'}")
                st.write(f"**Website:** {website or 'Not provided'}")
                st.write(f"**Location:** {location or 'Not provided'}")
                st.write(f"**Credits:** {credits}")
                st.write(f"**Profile Complete:** {'Yes' if profile_complete else 'No'}")
                
                if company_description:
                    st.write("**Company Description:**")
                    st.write(company_description)
        
        # Add credits section for job givers
        if user_type == 'job_giver':
            st.subheader("Add Credits")
            credit_amount = st.number_input("Credit Amount", min_value=1, value=10, step=1, key="admin_credit_amount")
            
            if st.button("Add Credits", key="admin_add_credits_button"):
                job_giver = JobGiver.get_by_user_id(user_id)
                if job_giver and job_giver.add_credits(credit_amount):
                    st.success(f"Added {credit_amount} credits to {username}'s account")
                else:
                    st.error("Failed to add credits")
    
    except Exception as e:
        st.error(f"Error retrieving user details: {e}")
    finally:
        cursor.close()
        conn.close()

def redemption_requests():
    """View and process redemption requests"""
    st.header("Redemption Requests")
    
    # Get database connection
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get pending redemption requests
        cursor.execute("""
            SELECT 
                r.id,
                u.username,
                js.full_name,
                r.amount,
                r.upi_id,
                r.whatsapp_number,
                r.status,
                r.created_at
            FROM redemption_requests r
            JOIN users u ON r.user_id = u.id
            JOIN job_seekers js ON r.job_seeker_id = js.id
            ORDER BY 
                CASE WHEN r.status = 'pending' THEN 0 ELSE 1 END,
                r.created_at DESC
        """)
        
        requests = cursor.fetchall()
        
        if requests:
            # Create tabs for pending and processed requests
            pending_tab, processed_tab = st.tabs(["Pending Requests", "Processed Requests"])
            
            # Filter requests by status
            pending_requests = [r for r in requests if r[6] == 'pending']
            processed_requests = [r for r in requests if r[6] != 'pending']
            
            with pending_tab:
                if pending_requests:
                    st.write(f"**{len(pending_requests)} Pending Requests**")
                    
                    for req in pending_requests:
                        req_id, username, full_name, amount, upi_id, whatsapp, status, created_at = req
                        
                        with st.expander(f"Request #{req_id} - {full_name} - {amount} Credits"):
                            st.write(f"**Username:** {username}")
                            st.write(f"**Full Name:** {full_name}")
                            st.write(f"**Amount:** {amount} Credits")
                            st.write(f"**UPI ID:** {upi_id}")
                            st.write(f"**WhatsApp:** {whatsapp}")
                            st.write(f"**Requested:** {created_at}")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button("Mark as Completed", key=f"complete_{req_id}"):
                                    cursor.execute("""
                                        UPDATE redemption_requests
                                        SET status = 'completed', processed_at = NOW()
                                        WHERE id = %s
                                    """, (req_id,))
                                    
                                    conn.commit()
                                    st.success(f"Request #{req_id} marked as completed")
                                    st.rerun()
                            
                            with col2:
                                if st.button("Reject Request", key=f"reject_{req_id}"):
                                    cursor.execute("""
                                        UPDATE redemption_requests
                                        SET status = 'rejected', processed_at = NOW()
                                        WHERE id = %s
                                    """, (req_id,))
                                    
                                    # Return credits to the user
                                    cursor.execute("""
                                        UPDATE job_seekers js
                                        SET credits = credits + %s
                                        FROM redemption_requests r
                                        WHERE r.id = %s AND js.id = r.job_seeker_id
                                    """, (amount, req_id))
                                    
                                    # Record the transaction
                                    cursor.execute("""
                                        INSERT INTO credit_transactions 
                                        (user_id, amount, transaction_type, description)
                                        SELECT user_id, %s, 'refund', 'Redemption request rejected, credits refunded'
                                        FROM redemption_requests
                                        WHERE id = %s
                                    """, (amount, req_id))
                                    
                                    conn.commit()
                                    st.success(f"Request #{req_id} rejected and credits refunded")
                                    st.rerun()
                else:
                    st.info("No pending redemption requests")
            
            with processed_tab:
                if processed_requests:
                    st.write(f"**{len(processed_requests)} Processed Requests**")
                    
                    # Convert to DataFrame for easier display
                    processed_df = pd.DataFrame(
                        processed_requests,
                        columns=["ID", "Username", "Full Name", "Amount", "UPI ID", "WhatsApp", "Status", "Requested At"]
                    )
                    
                    st.dataframe(processed_df)
                else:
                    st.info("No processed redemption requests")
        else:
            st.info("No redemption requests found")
    
    except Exception as e:
        st.error(f"Error retrieving redemption requests: {e}")
    finally:
        cursor.close()
        conn.close()

def credit_transactions():
    """View credit transactions"""
    st.header("Credit Transactions")
    
    # Get database connection
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get transactions
        cursor.execute("""
            SELECT 
                ct.id,
                u.username,
                u.user_type,
                ct.amount,
                ct.transaction_type,
                ct.description,
                ct.created_at
            FROM credit_transactions ct
            JOIN users u ON ct.user_id = u.id
            ORDER BY ct.created_at DESC
            LIMIT 100
        """)
        
        transactions = cursor.fetchall()
        
        if transactions:
            trans_df = pd.DataFrame(
                transactions,
                columns=["ID", "Username", "User Type", "Amount", "Type", "Description", "Date"]
            )
            trans_df["User Type"] = trans_df["User Type"].apply(
                lambda x: "Candidate" if x == "job_seeker" else "Recruiter"
            )
            
            st.dataframe(trans_df)
            
            # Summary statistics
            st.subheader("Transaction Summary")
            
            cursor.execute("""
                SELECT 
                    SUM(amount) FILTER (WHERE transaction_type = 'purchase') AS purchased,
                    SUM(amount) FILTER (WHERE transaction_type = 'redemption') AS redeemed,
                    SUM(amount) FILTER (WHERE transaction_type = 'match') AS matches
                FROM credit_transactions
            """)
            
            summary = cursor.fetchone()
            purchased, redeemed, matches = summary
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Credits Purchased", purchased or 0)
            col2.metric("Total Credits Redeemed", abs(redeemed or 0))
            col3.metric("Total Match Transfers", abs(matches or 0))
        else:
            st.info("No transactions found")
    
    except Exception as e:
        st.error(f"Error retrieving transactions: {e}")
    finally:
        cursor.close()
        conn.close()

def system_settings():
    """System settings section"""
    st.header("System Settings")
    settings_tab1, settings_tab2, settings_tab2_credit_packages, settings_tab3 = st.tabs(["Admin Users", "Platform Settings", "Credit Packages", "System Info"])
    
    with settings_tab1:
        manage_admin_users()
    
    with settings_tab2:
        st.subheader("Platform Settings")
        
        conn_settings = get_connection()
        if conn_settings is None:
            st.error("Database connection failed. Cannot load or save platform settings.")
        else:
            try:
                cursor_settings = conn_settings.cursor()

                # Define keys for settings
                KEY_JOB_POST_COST = "job_post_cost"
                KEY_VIEW_MATCH_COST = "view_match_cost"
                KEY_CREDITS_PER_MATCH_JOB_SEEKER = "credits_per_match_job_seeker"
                KEY_REDEEM_CREDITS_THRESHOLD_JS = "redeem_credits_threshold_job_seeker"

                # Default values
                default_job_post_cost = 10
                default_view_match_cost = 5
                default_credits_per_match_job_seeker = 2
                default_redeem_credits_threshold_js = 100 # Default for job seeker redemption

                # Load current settings from database
                cursor_settings.execute(
                    "SELECT key, value FROM platform_settings WHERE key IN (%s, %s, %s, %s)",
                    (KEY_JOB_POST_COST, KEY_VIEW_MATCH_COST, KEY_CREDITS_PER_MATCH_JOB_SEEKER, KEY_REDEEM_CREDITS_THRESHOLD_JS)
                )
                current_settings_db = {row[0]: int(row[1]) for row in cursor_settings.fetchall()}

                loaded_job_post_cost = current_settings_db.get(KEY_JOB_POST_COST, default_job_post_cost)
                loaded_view_match_cost = current_settings_db.get(KEY_VIEW_MATCH_COST, default_view_match_cost)
                loaded_credits_per_match_job_seeker = current_settings_db.get(
                    KEY_CREDITS_PER_MATCH_JOB_SEEKER, default_credits_per_match_job_seeker
                )
                loaded_redeem_credits_threshold_js = current_settings_db.get(
                    KEY_REDEEM_CREDITS_THRESHOLD_JS, default_redeem_credits_threshold_js
                )

                # Credit pricing settings
                st.write("### Credit Pricing")
                col1_price, col2_price = st.columns(2)
                with col1_price:
                    job_post_cost = st.number_input(
                        "Cost to post a job (credits)", 
                        min_value=1, 
                        value=loaded_job_post_cost, 
                        key="setting_job_post_cost"
                    )
                with col2_price:
                    view_match_cost = st.number_input(
                        "Cost to view a match (credits)", 
                        min_value=1, 
                        value=loaded_view_match_cost, 
                        key="setting_view_match_cost"
                    )
                
                # Match settings
                st.write("### Match Settings")
                col1_match, _ = st.columns(2) # Use _ if second column is not needed here
                with col1_match:
                    credits_per_match = st.number_input(
                        "Credits earned per match (job seekers)", 
                        min_value=0,  # Can be 0 if no credits are earned
                        value=loaded_credits_per_match_job_seeker, 
                        key="setting_credits_per_match_job_seeker"
                    )
                
                st.write("### Job Seeker Settings")
                col1_js, _ = st.columns(2)
                with col1_js:
                    redeem_threshold_js = st.number_input(
                        "Minimum credits to redeem (job seekers)",
                        min_value=1, # Should be at least 1
                        value=loaded_redeem_credits_threshold_js,
                        key="setting_redeem_credits_threshold_js"
                    )
                
                if st.button("Save Settings", key="save_platform_settings_button"):
                    settings_to_save = [
                        (KEY_JOB_POST_COST, job_post_cost),
                        (KEY_VIEW_MATCH_COST, view_match_cost),
                        (KEY_CREDITS_PER_MATCH_JOB_SEEKER, credits_per_match),
                        (KEY_REDEEM_CREDITS_THRESHOLD_JS, redeem_threshold_js) # Add new setting to save
                    ]
                    
                    try:
                        for key, value in settings_to_save:
                            cursor_settings.execute("""
                                INSERT INTO platform_settings (key, value) VALUES (%s, %s)
                                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
                            """, (key, str(value)))
                        conn_settings.commit()
                        st.success("Settings saved successfully!")
                        st.rerun()
                    except Exception as e:
                        conn_settings.rollback()
                        st.error(f"Error saving settings: {e}")
            finally:
                if 'cursor_settings' in locals() and cursor_settings:
                    cursor_settings.close()
                if conn_settings:
                    conn_settings.close()
    
    with settings_tab2_credit_packages:
        manage_credit_packages()

    with settings_tab3:
        st.subheader("System Information")
        
        # Database connection status
        st.write("### Database Connection")
        if st.session_state.db_connected:
            st.success("Database connected successfully")
        else:
            st.error("Database connection failed - running in demo mode")
        
        # System stats
        st.write("### System Statistics")
        conn = get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Get table counts
                tables = ["users", "job_seekers", "job_givers", "jobs", "matches", "swipes", "credit_transactions"]
                counts = {}
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                
                # Display counts
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Users", counts["users"])
                col2.metric("Total Jobs", counts["jobs"])
                col3.metric("Total Matches", counts["matches"])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Job Seekers", counts["job_seekers"])
                col2.metric("Job Givers", counts["job_givers"])
                col3.metric("Total Swipes", counts["swipes"])
                
            except Exception as e:
                st.error(f"Error retrieving system stats: {e}")
            finally:
                cursor.close()
                conn.close()

def manage_jobs():
    """Manage jobs section"""
    st.header("Manage Jobs")
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filter by status",
            ["All Jobs", "Active Jobs", "Inactive Jobs"],
            key="job_status_filter"
        )
    
    # Get database connection
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Build query based on filter
        query = """
            SELECT j.id, j.title, jg.company_name, j.location, j.job_type, j.created_at, j.active
            FROM jobs j
            JOIN job_givers jg ON j.job_giver_id = jg.id
        """
        
        if status_filter == "Active Jobs":
            query += " WHERE j.active = TRUE"
        elif status_filter == "Inactive Jobs":
            query += " WHERE j.active = FALSE"
        
        query += " ORDER BY j.created_at DESC"
        
        cursor.execute(query)
        jobs = cursor.fetchall()
        
        if jobs:
            job_df = pd.DataFrame(
                jobs,
                columns=["ID", "Title", "Company", "Location", "Job Type", "Created At", "Active"]
            )
            job_df["Active"] = job_df["Active"].apply(lambda x: "✅" if x else "❌")
            
            st.dataframe(job_df)
            
            # Job details section
            st.subheader("Job Details")
            selected_job_id = st.number_input("Enter Job ID to view details", min_value=1, step=1, key="selected_job_id")
            
            # Store the selected job ID in session state to persist across reruns
            if st.button("View Job Details", key="view_job_details_button"):
                st.session_state.viewing_job_id = selected_job_id
                show_job_details(selected_job_id)
            
            # If we have a job ID in session state, show its details
            elif 'viewing_job_id' in st.session_state:
                show_job_details(st.session_state.viewing_job_id)
        else:
            st.info("No jobs found")
    
    except Exception as e:
        st.error(f"Error retrieving jobs: {e}")
    finally:
        cursor.close()
        conn.close()

def manage_credit_packages():
    """Manage credit packages section"""
    st.subheader("Manage Credit Packages")

    # Display existing packages
    st.write("### Existing Credit Packages")
    packages = CreditPackage.get_all(include_inactive=True)
    if packages:
        package_data = [{
            "ID": p.id, "Name": p.name, "Description": p.description,
            "Credits": p.credits_amount, "Price (INR)": f"{p.price_inr:.2f}",
            "Active": "✅" if p.is_active else "❌", "Order": p.sort_order
        } for p in packages]
        st.dataframe(pd.DataFrame(package_data))
    else:
        st.info("No credit packages found.")

    st.write("---")

    # Add/Edit Package Form
    # Use session state to manage edit mode
    if 'editing_package_id' not in st.session_state:
        st.session_state.editing_package_id = None

    if st.session_state.editing_package_id:
        st.write(f"### Edit Package ID: {st.session_state.editing_package_id}")
        package_to_edit = CreditPackage.get_by_id(st.session_state.editing_package_id)
    else:
        st.write("### Add New Credit Package")
        package_to_edit = None # For new package

    with st.form(key="credit_package_form"):
        name = st.text_input("Package Name", value=package_to_edit.name if package_to_edit else "")
        description = st.text_area("Description (optional)", value=package_to_edit.description if package_to_edit else "")
        credits_amount = st.number_input("Credits Amount", min_value=1, step=1, value=package_to_edit.credits_amount if package_to_edit else 10)
        # For price, ensure it's treated as float for number_input
        price_inr_float = float(package_to_edit.price_inr) if package_to_edit and package_to_edit.price_inr is not None else 0.0
        price_inr = st.number_input("Price (INR)", min_value=0.0, step=0.01, format="%.2f", value=price_inr_float)
        
        col1_form, col2_form = st.columns(2)
        with col1_form:
            is_active = st.checkbox("Is Active?", value=package_to_edit.is_active if package_to_edit else True)
        with col2_form:
            sort_order = st.number_input("Sort Order (lower numbers appear first)", min_value=0, step=1, value=package_to_edit.sort_order if package_to_edit else 0)

        submit_button_label = "Update Package" if st.session_state.editing_package_id else "Add Package"
        submitted = st.form_submit_button(submit_button_label)

        if submitted:
            if not name or credits_amount <= 0 or price_inr < 0:
                st.error("Package Name, valid Credits Amount, and Price are required.")
            else:
                if st.session_state.editing_package_id:
                    success = CreditPackage.update(
                        st.session_state.editing_package_id, name, description, credits_amount,
                        price_inr, is_active, sort_order
                    )
                    if success:
                        st.success(f"Package '{name}' updated successfully!")
                        st.session_state.editing_package_id = None # Exit edit mode
                        CreditPackage.clear_all_caches()
                        st.rerun()
                    else:
                        st.error("Failed to update package.")
                else: # Adding new package
                    package_id = CreditPackage.create(
                        name, description, credits_amount, price_inr,
                        is_active, sort_order
                    )
                    if package_id:
                        st.success(f"Package '{name}' added successfully with ID {package_id}!")
                        CreditPackage.clear_all_caches()
                        st.rerun()
                    else:
                        st.error("Failed to add package.")
    
    if st.session_state.editing_package_id:
        if st.button("Cancel Edit"):
            st.session_state.editing_package_id = None
            st.rerun()

    st.write("---")
    st.write("### Actions on Existing Packages")
    package_id_action = st.number_input("Enter Package ID for Action", min_value=1, step=1, key="pkg_id_action")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("Edit Selected Package", key="edit_pkg_btn"):
            if CreditPackage.get_by_id(package_id_action):
                st.session_state.editing_package_id = package_id_action
                st.rerun()
            else:
                st.error(f"Package ID {package_id_action} not found.")
    with col_act2:
        if st.button("Delete Selected Package", key="delete_pkg_btn"):
            if CreditPackage.delete(package_id_action):
                st.success(f"Package ID {package_id_action} deleted.")
                CreditPackage.clear_all_caches()
                st.rerun()
            else:
                st.error(f"Failed to delete package ID {package_id_action} or package not found.")

def show_job_details(job_id):
    """Show details for a specific job"""
    # Check if we have a status change message to display
    if st.session_state.get('job_status_changed', False):
        st.success(st.session_state.get('job_status_message', 'Job status updated successfully'))
        # Clear the flag so the message doesn't show again on refresh
        st.session_state.job_status_changed = False
    
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get job info
        cursor.execute("""
            SELECT j.id, j.title, j.description, j.requirements, j.location, j.salary_range, 
                   j.job_type, j.created_at, j.active, jg.company_name, jg.id as job_giver_id
            FROM jobs j
            JOIN job_givers jg ON j.job_giver_id = jg.id
            WHERE j.id = %s
        """, (job_id,))
        
        job = cursor.fetchone()
        if not job:
            st.error("Job not found")
            return
        
        id, title, description, requirements, location, salary_range, job_type, created_at, active, company_name, job_giver_id = job
        
        # Display job details
        st.write(f"### {title}")
        st.write(f"**Company:** {company_name}")
        st.write(f"**Location:** {location}")
        st.write(f"**Job Type:** {job_type}")
        st.write(f"**Salary Range:** {salary_range}")
        st.write(f"**Posted:** {created_at}")
        st.write(f"**Status:** {'Active' if active else 'Inactive'}")
        
        st.write("**Description:**")
        st.write(description)
        
        if requirements:
            st.write("**Requirements:**")
            for req in requirements:
                st.write(f"- {req}")
        
        # Job actions
        st.subheader("Job Actions")
        
        # Activation/Deactivation Button (outside the delete form)
        
        if active:
            if st.button("Deactivate Job", key=f"deactivate_job_{job_id}"):
                if Job.set_active_status(job_id, False):
                    # Use a session state flag to track the change
                    st.session_state.job_status_changed = True
                    st.session_state.job_status_message = "Job deactivated successfully"
                    st.rerun()
                else:
                    st.error("Error deactivating job. Please try again.")
        else:
            if st.button("Activate Job", key=f"activate_job_{job_id}"):
                if Job.set_active_status(job_id, True):
                    # Use a session state flag to track the change
                    st.session_state.job_status_changed = True
                    st.session_state.job_status_message = "Job activated successfully"
                    st.rerun()
                else:
                    st.error("Error activating job. Please try again.")
        
        # Deletion Form
        with st.form(key=f"delete_job_form_{job_id}"):
            st.warning("Deleting a job is permanent and cannot be undone.")
            # Display the checkbox first
            confirm_delete = st.checkbox("Confirm deletion", key=f"confirm_delete_{job_id}")
            submitted = st.form_submit_button("Delete Job Permanently")
            
            if submitted:
                # Confirm deletion
                if confirm_delete:
                    try:
                        # First, delete related records (e.g., matches)
                        st.write("Deleting related matches...") # Give user feedback
                        cursor.execute("DELETE FROM matches WHERE job_id = %s", (job_id,))
                        
                        # Second, delete related swipes (where the job was the target)
                        # This is necessary if job seekers have swiped on this job
                        st.write("Deleting related swipes...") # Give user feedback
                        cursor.execute("DELETE FROM swipes WHERE target_type = 'job' AND target_id = %s", (job_id,))


                        # Now, delete the job itself
                        st.write("Deleting job...") # Give user feedback
                        cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
                        
                        # Commit the transaction
                        conn.commit()
                        st.success(f"Job ID {job_id} and related records (matches, swipes) deleted successfully.")
                        # Consider removing rerun or placing it outside the form if causing issues, but likely okay here.
                    except Exception as delete_error:
                        conn.rollback() # Rollback transaction on error
                        st.error(f"Error deleting job ID {job_id}:")
                        st.exception(delete_error) # Display the full exception traceback
                        st.warning("The job was not deleted. Please check logs or database constraints.")
        
        # Show match statistics
        st.subheader("Match Statistics")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM matches 
            WHERE job_id = %s
        """, (job_id,))
        
        match_count = cursor.fetchone()[0]
        st.write(f"This job has {match_count} matches.")
        
        if match_count > 0:
            cursor.execute("""
                SELECT m.id, js.full_name, m.created_at, m.status
                FROM matches m
                JOIN job_seekers js ON m.job_seeker_id = js.id
                WHERE m.job_id = %s
                ORDER BY m.created_at DESC
            """, (job_id,))
            
            matches = cursor.fetchall()
            match_df = pd.DataFrame(
                matches,
                columns=["Match ID", "Candidate", "Matched At", "Status"]
            )
            st.dataframe(match_df)
    
    except Exception as e:
        st.error(f"Error retrieving job details: {e}")
    finally:
        cursor.close()
        conn.close()

def manage_admin_users():
    """Manage admin users section"""
    st.subheader("Admin Users")
    
    # List existing admin users
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get admin users
        cursor.execute("""
            SELECT id, username, email, created_at
            FROM users
            WHERE user_type = 'admin'
            ORDER BY created_at DESC
        """)
        
        admin_users = cursor.fetchall()
        
        if admin_users:
            st.write("### Existing Admin Users")
            admin_df = pd.DataFrame(
                admin_users,
                columns=["ID", "Username", "Email", "Created At"]
            )
            st.dataframe(admin_df)
        
        # Create new admin user form
        st.write("### Create New Admin User")
        with st.form("create_admin_form"):
            new_admin_username = st.text_input("Username", key="new_admin_username")
            new_admin_email = st.text_input("Email", key="new_admin_email")
            new_admin_password = st.text_input("Password", type="password", key="new_admin_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_admin_password")
            
            submit_button = st.form_submit_button("Create Admin User")
            
            if submit_button:
                if not new_admin_username or not new_admin_email or not new_admin_password:
                    st.error("Please fill in all fields")
                elif new_admin_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Check if username already exists
                    cursor.execute("SELECT id FROM users WHERE username = %s", (new_admin_username,))
                    if cursor.fetchone():
                        st.error("Username already exists")
                    else:
                        # Create new admin user
                        try:
                            cursor.execute("""
                                INSERT INTO users (username, email, password_hash, user_type)
                                VALUES (%s, %s, %s, 'admin')
                            """, (
                                new_admin_username,
                                new_admin_email,
                                User.hash_password(new_admin_password)
                            ))
                            conn.commit()
                            st.success(f"Admin user '{new_admin_username}' created successfully")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Error creating admin user: {e}")
    
    except Exception as e:
        st.error(f"Error managing admin users: {e}")
    finally:
        cursor.close()
        conn.close()

def manage_user_credits():
    """Manage user credits section"""
    st.header("Manage User Credits")
    
    # Get database connection
    conn = get_connection()
    if conn is None:
        st.error("Could not connect to database")
        return
    
    try:
        cursor = conn.cursor()
        
        # Get all users with their credit balances
        cursor.execute("""
            SELECT 
                u.id,
                u.username,
                u.user_type,
                COALESCE(jg.credits, 0) as job_giver_credits,
                COALESCE(js.credits, 0) as job_seeker_credits
            FROM users u
            LEFT JOIN job_givers jg ON u.id = jg.user_id
            LEFT JOIN job_seekers js ON u.id = js.user_id
            WHERE u.user_type != 'admin'
            ORDER BY u.username
        """)
        
        users = cursor.fetchall()
        
        if users:
            # Create DataFrame for display
            user_df = pd.DataFrame(
                users,
                columns=["ID", "Username", "User Type", "Job Giver Credits", "Job Seeker Credits"]
            )
            
            # Format user type for display
            user_df["User Type"] = user_df["User Type"].apply(
                lambda x: "Candidate" if x == "job_seeker" else "Recruiter"
            )
            
            # Add checkbox column for bulk selection
            user_df["Select"] = False
            
            # Display users and their credit balances with checkboxes
            edited_df = st.data_editor(
                user_df,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select users to reset credits",
                        default=False,
                    ),
                    "ID": st.column_config.NumberColumn(
                        "ID",
                        help="User ID",
                        disabled=True,
                    ),
                    "Username": st.column_config.TextColumn(
                        "Username",
                        help="User's username",
                        disabled=True,
                    ),
                    "User Type": st.column_config.TextColumn(
                        "User Type",
                        help="Type of user",
                        disabled=True,
                    ),
                    "Job Giver Credits": st.column_config.NumberColumn(
                        "Job Giver Credits",
                        help="Current credit balance for recruiters",
                        disabled=True,
                    ),
                    "Job Seeker Credits": st.column_config.NumberColumn(
                        "Job Seeker Credits",
                        help="Current credit balance for candidates",
                        disabled=True,
                    ),
                },
                hide_index=True,
            )
            
            # Bulk reset credits section
            st.subheader("Bulk Credit Reset")
            st.warning("""
            ⚠️ **Warning**: This action will reset credits to zero for all selected users.
            This action cannot be undone. Please ensure you have selected the correct users.
            """)
            
            if st.button("Reset Credits for Selected Users"):
                selected_users = edited_df[edited_df["Select"] == True]
                
                if len(selected_users) == 0:
                    st.error("Please select at least one user to reset credits")
                else:
                    try:
                        # Start transaction
                        cursor.execute("BEGIN")
                        
                        for _, user in selected_users.iterrows():
                            user_id = user["ID"]
                            user_type = "job_giver" if user["User Type"] == "Recruiter" else "job_seeker"
                            current_credits = user["Job Giver Credits"] if user_type == "job_giver" else user["Job Seeker Credits"]
                            
                            # Only reset if user has credits
                            if current_credits > 0:
                                # Update credits to zero
                                if user_type == "job_giver":
                                    cursor.execute(
                                        """
                                        UPDATE job_givers
                                        SET credits = 0
                                        WHERE user_id = %s
                                        """,
                                        (user_id,)
                                    )
                                else:  # job_seeker
                                    cursor.execute(
                                        """
                                        UPDATE job_seekers
                                        SET credits = 0
                                        WHERE user_id = %s
                                        """,
                                        (user_id,)
                                    )
                                
                                # Record the transaction
                                cursor.execute(
                                    """
                                    INSERT INTO credit_transactions 
                                    (user_id, amount, transaction_type, description)
                                    VALUES (%s, %s, %s, %s)
                                    """,
                                    (user_id, -current_credits, 'admin_reset', 'Credits reset to zero by admin')
                                )
                        
                        # Commit transaction
                        conn.commit()
                        st.success(f"Successfully reset credits for {len(selected_users)} users")
                        st.rerun()
                        
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error resetting credits: {e}")
            
            # Individual credit modification form
            st.subheader("Modify Individual User Credits")
            
            # User selection
            selected_user = st.selectbox(
                "Select User",
                options=[(row[0], f"{row[1]} ({row[2]})") for row in users],
                format_func=lambda x: x[1]
            )
            
            if selected_user:
                user_id = selected_user[0]
                user_type = next(row[2] for row in users if row[0] == user_id)
                
                # Get current credit balance
                current_credits = next(
                    row[3] if user_type == "job_giver" else row[4]
                    for row in users if row[0] == user_id
                )
                
                st.write(f"Current Credit Balance: {current_credits}")
                
                # Credit modification form
                with st.form("modify_credits_form"):
                    credit_change = st.number_input(
                        "Credit Change Amount",
                        min_value=-1000,
                        max_value=1000,
                        value=0,
                        help="Enter positive number to add credits, negative to remove"
                    )
                    
                    reason = st.text_area(
                        "Reason for Credit Change",
                        help="Please provide a reason for this credit modification"
                    )
                    
                    submit_button = st.form_submit_button("Apply Credit Change")
                    
                    if submit_button:
                        if not reason:
                            st.error("Please provide a reason for the credit change")
                        else:
                            try:
                                # Start transaction
                                cursor.execute("BEGIN")
                                
                                # Update credits based on user type
                                if user_type == "job_giver":
                                    cursor.execute(
                                        """
                                        UPDATE job_givers
                                        SET credits = credits + %s
                                        WHERE user_id = %s
                                        RETURNING credits
                                        """,
                                        (credit_change, user_id)
                                    )
                                else:  # job_seeker
                                    cursor.execute(
                                        """
                                        UPDATE job_seekers
                                        SET credits = credits + %s
                                        WHERE user_id = %s
                                        RETURNING credits
                                        """,
                                        (credit_change, user_id)
                                    )
                                
                                new_balance = cursor.fetchone()[0]
                                
                                # Record the transaction
                                cursor.execute(
                                    """
                                    INSERT INTO credit_transactions 
                                    (user_id, amount, transaction_type, description)
                                    VALUES (%s, %s, %s, %s)
                                    """,
                                    (user_id, credit_change, 'admin_adjustment', f'Admin adjustment: {reason}')
                                )
                                
                                # Commit transaction
                                conn.commit()
                                
                                st.success(f"Credit balance updated successfully! New balance: {new_balance}")
                                st.rerun()
                                
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Error updating credits: {e}")
        else:
            st.info("No users found")
    
    except Exception as e:
        st.error(f"Error managing user credits: {e}")
    finally:
        cursor.close()
        conn.close()