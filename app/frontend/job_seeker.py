import streamlit as st
import os
import pandas as pd
from app.models.job_seeker import JobSeeker
from app.models.job import Job
from app.models.swipe import Swipe
from app.models.match import Match
from app.database.connection import get_connection
from app.utils.settings import get_platform_setting # Import the new utility

# --- New: Define upload paths more flexibly ---
# Determine the project root dynamically.
# This assumes job_seeker.py is in app/frontend/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Default base directory for uploads, relative to the project root.
# This will be used for local development if the environment variable isn't set.
DEFAULT_UPLOADS_BASE_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Get the base path for uploads from an environment variable (e.g., JOBMATCH_UPLOADS_DIR).
# If the env var is not set, it falls back to DEFAULT_UPLOADS_BASE_DIR.
# On Render, you would set JOBMATCH_UPLOADS_DIR to your persistent disk mount point (e.g., /mnt/data/uploads).
UPLOADS_BASE_DIR = os.environ.get("JOBMATCH_UPLOADS_DIR", DEFAULT_UPLOADS_BASE_DIR)

# Specific directory for CVs, within the determined UPLOADS_BASE_DIR
CV_UPLOADS_DIR = os.path.join(UPLOADS_BASE_DIR, "cvs")
# --- End New ---

def job_seeker_dashboard():
    """Dashboard for job seekers"""
    # Get job seeker profile
    job_seeker = JobSeeker.get_by_user_id(st.session_state.user_id)
    
    # Debug info
    print(f"Job Seeker Dashboard - User ID: {st.session_state.user_id}")
    if job_seeker:
        print(f"Job Seeker ID: {job_seeker.id}, Credits: {job_seeker.credits}")
    
    # Sidebar menu
    menu = st.sidebar.radio(
        "Menu",
        ["Profile", "Swipe Jobs", "My Matches", "Credits"],
        key="job_seeker_menu"
    )
    
    # Check if profile is complete
    if not job_seeker or not job_seeker.profile_complete:
        if menu != "Profile":
            st.warning("Please complete your profile first")
            menu = "Profile"
    
    # Display appropriate section based on menu selection
    if menu == "Profile":
        profile_section(job_seeker)
    elif menu == "Swipe Jobs":
        swipe_section(job_seeker)
    elif menu == "My Matches":
        matches_section(job_seeker)
    elif menu == "Credits":
        credits_section(job_seeker)

def profile_section(job_seeker):
    """Profile management section for job seekers"""
    st.title("My Profile")
    
    # Initialize job seeker if it doesn't exist
    if not job_seeker:
        job_seeker = JobSeeker(user_id=st.session_state.user_id)
    
    # Profile form
    with st.form("job_seeker_profile_form"):
        full_name = st.text_input("Full Name", value=job_seeker.full_name or "", key="js_full_name")
        
        col1, col2 = st.columns(2)
        with col1:
            location = st.text_input("Location", value=job_seeker.location or "", key="js_location")
        with col2:
            experience = st.number_input("Years of Experience", 
                                        value=job_seeker.experience or 0,
                                        min_value=0, max_value=50,
                                        key="js_experience")
        
        education = st.text_input("Education", value=job_seeker.education or "", key="js_education")
        
        # Skills input (comma-separated)
        skills_str = ", ".join(job_seeker.skills) if job_seeker.skills else ""
        skills_input = st.text_input("Skills (comma-separated)", value=skills_str, key="js_skills")
        
        bio = st.text_area("Bio / About Me", value=job_seeker.bio or "", height=150, key="js_bio")
        
        # CV upload
        st.write("Upload your CV (PDF format)")
        cv_file = st.file_uploader("Choose a file", type=["pdf"], key="js_cv_upload")
        
        submit_button = st.form_submit_button("Save Profile")
        
        if submit_button:
            # Process form data
            if not full_name:
                st.error("Full name is required")
                return
            
            # Process skills (split by comma and strip whitespace)
            skills_list = [skill.strip() for skill in skills_input.split(",") if skill.strip()]
            
            # Save CV file if uploaded
            cv_path_to_save = job_seeker.cv_path # Keep current path if no new file
            if cv_file:
                # Create directory if it doesn't exist, using the new CV_UPLOADS_DIR
                os.makedirs(CV_UPLOADS_DIR, exist_ok=True)
                
                # Save file to the new CV_UPLOADS_DIR
                # Use os.path.join for platform-independent path construction
                cv_path_to_save = os.path.join(CV_UPLOADS_DIR, f"{st.session_state.user_id}_{cv_file.name}")
                try:
                    with open(cv_path_to_save, "wb") as f:
                        f.write(cv_file.getbuffer())
                    st.info(f"CV will be saved to: {cv_path_to_save}") # Optional: for debugging
                except Exception as e:
                    st.error(f"Error saving CV: {e}")
                    cv_path_to_save = job_seeker.cv_path # Revert to old path on error
            
            # Update job seeker object
            job_seeker.full_name = full_name
            job_seeker.bio = bio
            job_seeker.skills = skills_list
            job_seeker.experience = experience
            job_seeker.education = education
            job_seeker.location = location
            job_seeker.cv_path = cv_path_to_save # Use the potentially updated path
            
            # Save to database
            if job_seeker.update_profile():
                st.success("Profile updated successfully!")
            else:
                st.error("Failed to update profile. Please try again.")
    
    # Display current profile if complete
    if job_seeker.profile_complete:
        st.subheader("Current Profile")
        
        st.write(f"**Name:** {job_seeker.full_name}")
        st.write(f"**Location:** {job_seeker.location}")
        st.write(f"**Experience:** {job_seeker.experience} years")
        st.write(f"**Education:** {job_seeker.education}")
        
        if job_seeker.skills:
            st.write("**Skills:**")
            st.write(", ".join(job_seeker.skills))
        
        if job_seeker.bio:
            st.write("**About Me:**")
            st.write(job_seeker.bio)
        
        if job_seeker.cv_path:
            st.write("**CV:** Uploaded ✓")

def swipe_section(job_seeker):
    """Job swiping section for job seekers"""
    st.title("Find Jobs")
    
    # Search form
    with st.expander("Search Jobs", expanded=True):
        st.write("Filter jobs by your preferences:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            keywords = st.text_input("Keywords (job title, skills, etc.)", key="job_search_keywords")
            location = st.text_input("Location", key="job_search_location")
        
        with col2:
            job_type = st.selectbox(
                "Job Type", 
                ["", "Full-time", "Part-time", "Contract", "Internship", "Remote"],
                key="job_search_type"
            )
            salary_range = st.text_input("Minimum Salary (e.g., 50000)", key="job_search_salary")
        
        # Button row for search and reset
        col1, col2 = st.columns(2)
        
        with col1:
            # Store search parameters in session state
            if st.button("Search", key="job_search_button"):
                st.session_state.job_search_params = {
                    "keywords": keywords if keywords.strip() else None,
                    "location": location if location.strip() else None,
                    "job_type": job_type if job_type else None,
                    "min_salary": salary_range if salary_range.strip() else None
                }
                # Reset job index when search parameters change
                st.session_state.job_index = 0
                st.success("Search filters applied!")
        
        with col2:
            # Reset filters button
            if st.button("Reset Filters", key="reset_filters_button"):
                # Clear search parameters
                st.session_state.job_search_params = {
                    "keywords": None,
                    "location": None,
                    "job_type": None,
                    "min_salary": None
                }
                # Reset job index
                st.session_state.job_index = 0
                
                # Reset left swipes to make previously swiped jobs available again
                success, message = Swipe.reset_left_swipes(st.session_state.user_id, 'job')
                
                if success:
                    st.success(f"Filters have been reset! {message.split(':')[0]}. All unmatched jobs are now available.")
                else:
                    st.warning("Filters have been reset, but there was an issue resetting swipe history.")
                    print(f"Error resetting swipes: {message}")
    
    # Initialize search params in session state if not present
    if "job_search_params" not in st.session_state:
        st.session_state.job_search_params = {
            "keywords": None,
            "location": None,
            "job_type": None,
            "min_salary": None
        }
    
    # Ensure all parameters are properly set to None if they're empty strings
    if st.session_state.job_search_params["keywords"] == "":
        st.session_state.job_search_params["keywords"] = None
    if st.session_state.job_search_params["location"] == "":
        st.session_state.job_search_params["location"] = None
    if st.session_state.job_search_params["min_salary"] == "":
        st.session_state.job_search_params["min_salary"] = None
    
    # Get jobs for swiping with search parameters
    jobs = Job.get_all_for_swiping(
        job_seeker.id, 
        limit=50,  # Increased limit to show more jobs
        keywords=st.session_state.job_search_params["keywords"],
        location=st.session_state.job_search_params["location"],
        job_type=st.session_state.job_search_params["job_type"],
        min_salary=st.session_state.job_search_params["min_salary"]
    )
    
    if not jobs:
        st.info("No jobs match your search criteria. Try adjusting your filters or reset to see previously skipped jobs.")
        
        # Add a button to reset left swipes
        if st.button("Show Previously Skipped Jobs", key="reset_skipped_jobs"):
            success, message = Swipe.reset_left_swipes(st.session_state.user_id, 'job')
            if success:
                st.success(f"{message.split(':')[0]}. Previously skipped jobs are now available.")
                st.rerun()
            else:
                st.warning("There was an issue resetting your swipe history.")
                print(f"Error resetting swipes: {message}")
        return
    
    # Initialize job index in session state if not present
    if "job_index" not in st.session_state:
        st.session_state.job_index = 0
    
    # Get current job
    if st.session_state.job_index < len(jobs):
        current_job = jobs[st.session_state.job_index]
        
        # Display job card
        with st.container():
            st.subheader(current_job.title)
            st.write(f"**Company:** {current_job.company_name}")
            st.write(f"**Location:** {current_job.location}")
            
            if current_job.salary_range:
                st.write(f"**Salary Range:** {current_job.salary_range}")
            
            if current_job.job_type:
                st.write(f"**Job Type:** {current_job.job_type}")
            
            st.write("**Description:**")
            st.write(current_job.description)
            
            if current_job.requirements:
                st.write("**Requirements:**")
                for req in current_job.requirements:
                    st.write(f"- {req}")
        
        # Swipe buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("👎 Lets see some more", key="swipe_left"):
                # Record left swipe
                swipe = Swipe(
                    user_id=st.session_state.user_id,
                    target_id=current_job.id,
                    target_type="job",
                    direction="left"
                )
                success, message = swipe.create()
                
                # Move to next job
                st.session_state.job_index += 1
                st.rerun()
        
        with col2:
            if st.button("👍 Match Please", key="swipe_right"):
                # Record right swipe
                swipe = Swipe(
                    user_id=st.session_state.user_id,
                    target_id=current_job.id,
                    target_type="job",
                    direction="right"
                )
                success, message = swipe.create()
                
                # Move to next job
                st.session_state.job_index += 1
                
                if success and "match" in message.lower():
                    st.balloons()
                    st.success("It's a match! 🎉 Check your matches tab.")
                
                # Get the next set of jobs if we've reached the end
                if st.session_state.job_index >= len(jobs):
                    # Get a fresh set of jobs
                    new_jobs = Job.get_all_for_swiping(
                        job_seeker.id, 
                        limit=50,  # Increased limit to show more jobs
                        keywords=st.session_state.job_search_params["keywords"],
                        location=st.session_state.job_search_params["location"],
                        job_type=st.session_state.job_search_params["job_type"],
                        min_salary=st.session_state.job_search_params["min_salary"]
                    )
                    
                    if not new_jobs:
                        st.session_state.job_index = 0
                
                st.rerun()
    else:
        st.info("You've seen all available jobs matching your current filters.")
        # Reset index for next time
        st.session_state.job_index = 0
        
        # Add a button to reset left swipes
        if st.button("Show Previously Skipped Jobs", key="end_reset_skipped_jobs"):
            success, message = Swipe.reset_left_swipes(st.session_state.user_id, 'job')
            if success:
                st.success(f"{message.split(':')[0]}. Previously skipped jobs are now available.")
                st.rerun()
            else:
                st.warning("There was an issue resetting your swipe history.")
                print(f"Error resetting swipes: {message}")

def matches_section(job_seeker):
    """Matches section for job seekers"""
    st.title("My Matches")
    
    # Debug info
    print(f"Fetching matches for job seeker ID: {job_seeker.id}")
    
    # Get matches for job seeker
    matches = Match.get_for_job_seeker(job_seeker.id)
    
    # More debug info
    print(f"Retrieved {len(matches)} matches for job seeker")
    
    if not matches:
        st.info("You don't have any matches yet. Start swiping to find jobs!")
        return
    
    # Display matches
    for match in matches:
        with st.expander(f"{match.job_title} at {match.company_name}"):
            st.write(f"**Matched on:** {match.created_at.strftime('%Y-%m-%d')}")
            st.write(f"**Status:** {match.status.capitalize()}")
            
            # Get job details
            job = Job.get_by_id(match.job_id)
            if job:
                st.write(f"**Location:** {job.location}")
                
                if job.salary_range:
                    st.write(f"**Salary Range:** {job.salary_range}")
                
                if job.job_type:
                    st.write(f"**Job Type:** {job.job_type}")
                
                st.write("**Description:**")
                st.write(job.description)
                
                if job.requirements:
                    st.write("**Requirements:**")
                    for req in job.requirements:
                        st.write(f"- {req}")

def credits_section(job_seeker):
    """Credits section for job seekers"""
    st.title("My Credits")
    
    # Display current credit balance
    st.header(f"Current Balance: {job_seeker.credits} credits")
    
    st.subheader("Redeem Credits")
    
    # Fetch the redeem threshold from platform settings, default to 100 if not set or error
    redeem_threshold = int(get_platform_setting("redeem_credits_threshold_job_seeker", 100))

    # Determine if the button should be disabled
    disable_redeem_button = job_seeker.credits < redeem_threshold

    # Check if we're in redemption form mode
    if "show_redemption_form" not in st.session_state:
        st.session_state.show_redemption_form = False
    
    # Use the dynamic threshold in the button label and logic
    if not st.session_state.show_redemption_form:
        if st.button(f"Redeem {redeem_threshold} Credits", disabled=disable_redeem_button, key="redeem_credits_button"):
            # First check if user has enough credits
            success, message = job_seeker.redeem_credits(amount_to_redeem=redeem_threshold)
            if success:
                # Show the redemption form
                st.session_state.show_redemption_form = True
                st.rerun()
            else:
                st.error(message)
    else:
        # Show the redemption form
        st.subheader("Complete Your Redemption")
        st.info("Please provide your UPI ID and WhatsApp number to receive your payment.")
        
        with st.form("redemption_form"):
            upi_id = st.text_input("UPI ID (e.g., name@upi)", key="upi_id")
            whatsapp_number = st.text_input("WhatsApp Number (with country code)", key="whatsapp_number")
            
            submit_button = st.form_submit_button("Submit Redemption Request")
            
            if submit_button:
                if not upi_id or not whatsapp_number:
                    st.error("Please provide both UPI ID and WhatsApp number.")
                else:
                    # Process the redemption request
                    success, message = job_seeker.create_redemption_request(
                        amount_to_redeem=redeem_threshold,
                        upi_id=upi_id,
                        whatsapp_number=whatsapp_number
                    )
                    
                    if success:
                        st.success(message)
                        st.balloons()
                        # Reset the form flag
                        st.session_state.show_redemption_form = False
                        st.rerun()  # Rerun to update the credit balance display
                    else:
                        st.error(message)
        
        # Add a cancel button
        if st.button("Cancel", key="cancel_redemption"):
            st.session_state.show_redemption_form = False
            st.rerun()
            
    if disable_redeem_button and not st.session_state.show_redemption_form:
        st.info(f"You need {redeem_threshold} credits to redeem. You currently have {job_seeker.credits} credits.")
        st.progress(job_seeker.credits / redeem_threshold if redeem_threshold > 0 else 1.0)
    
    # Transaction history
    st.subheader("Transaction History")
    
    # Get transaction history from database
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT amount, transaction_type, description, created_at
                FROM credit_transactions
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (st.session_state.user_id,))
            
            transactions = cursor.fetchall()
            
            if transactions:
                trans_df = pd.DataFrame(
                    transactions,
                    columns=["Amount", "Type", "Description", "Date"]
                )
                st.dataframe(trans_df)
            else:
                st.info("No transactions yet.")
        except Exception as e:
            st.error(f"Error retrieving transaction history: {e}")
        finally:
            cursor.close()
            conn.close()
    else:
        st.error("Could not connect to database")