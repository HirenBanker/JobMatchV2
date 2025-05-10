import streamlit as st
import pandas as pd
import os
from app.models.job_giver import JobGiver
from app.models.job import Job
from app.models.job_seeker import JobSeeker
from app.models.swipe import Swipe
from app.models.match import Match
from app.database.connection import get_connection
from app.models.credit_package import CreditPackage # Import the new model

# Callback function to set the target page for navigation
def set_navigation_target_page(target_page_title):
    st.session_state.navigate_to_page_title = target_page_title

def job_giver_dashboard():
    """Dashboard for job givers (recruiters)"""
    # Debug info - print all session state keys at the start
    print("Session state keys at start of job_giver_dashboard:", list(st.session_state.keys()))
    user_id_from_session = st.session_state.get('user_id')
    print(f"job_giver_dashboard: user_id_from_session = {user_id_from_session} (type: {type(user_id_from_session)})")
    print(f"Username in session: {st.session_state.get('username')}")
    print(f"User type in session: {st.session_state.get('user_type')}")
    
    # Make sure we have a valid user_id in session state
    if not user_id_from_session:
        print("No user_id in session state - redirecting to login")
        st.error("Session expired. Please log in again.")
        st.session_state.logged_in = False
        st.rerun()
        return
        
    # Initialize session state variables if they don't exist
    if 'job_giver_current_page' not in st.session_state:
        st.session_state.job_giver_current_page = "Profile"
        print("Initialized job_giver_current_page to Profile")

    # Get job giver profile directly from the database
    job_giver = JobGiver.get_by_user_id(user_id_from_session)
    
    # If we couldn't get the job_giver, show an error
    if not job_giver:
        print("Failed to load job_giver from database")
        st.error("Unable to load your profile. Please try refreshing the page.")
        if st.button("Refresh Page"):
            st.rerun()
        return
        
    # Debug info
    print(f"Job Giver Dashboard - User ID from object: {job_giver.user_id}")
    print(f"Job Giver ID: {job_giver.id}, Credits: {job_giver.credits}")
    print(f"Current page: {st.session_state.job_giver_current_page}")

    menu_options = ["Profile", "My Jobs", "Find Candidates", "My Matches", "Credits"]

    # Handle programmatic navigation (e.g., from buttons in other sections like "Go to Credits")
    # This ensures st.session_state.job_giver_current_page is set *before* the radio button reads it.
    if st.session_state.get("navigate_to_page_title"):
        print(f"Navigating to: {st.session_state.navigate_to_page_title}")
        st.session_state.job_giver_current_page = st.session_state.navigate_to_page_title
        del st.session_state.navigate_to_page_title

    # The radio button's state is directly managed by 'st.session_state.job_giver_current_page'.
    # Streamlit updates this session state variable when the radio button is changed and reruns.
    # The 'key' argument links the radio's state to this session state variable.
    # The return value of st.sidebar.radio is the selected option, which will also be
    # in st.session_state.job_giver_current_page after interaction.
    st.sidebar.radio(
        "Menu",
        menu_options,
        key="job_giver_current_page" 
    )
    
    # The 'menu' variable for logic should now be read directly from session state,
    # as the radio button directly updates it via its key.
    menu = st.session_state.job_giver_current_page
    
    print(f"Current menu selection: {menu}")

    # Check if profile is complete
    if not job_giver:
        print("job_giver object is None when checking profile completeness")
        st.error("Unable to load your profile. Please refresh the page.")
        if st.button("Refresh Page"):
            st.rerun()
        return
        
    if not job_giver.profile_complete:
        print(f"Profile is not complete. Current menu: {menu}")
        if menu != "Profile":
            st.warning("Please complete your profile first")
            menu = "Profile"
            st.session_state.job_giver_current_page = "Profile"
            print("Redirected to Profile page due to incomplete profile")
    
    # Display appropriate section based on menu selection
    try:
        print(f"Displaying section for menu: {menu}")
        if menu == "Profile":
            profile_section(job_giver)
        elif menu == "My Jobs":
            print("About to call jobs_section")
            jobs_section(job_giver)
            print("Returned from jobs_section")
        elif menu == "Find Candidates":
            candidates_section(job_giver)
        elif menu == "My Matches":
            matches_section(job_giver)
        elif menu == "Credits":
            credits_section(job_giver)
    except Exception as e:
        st.error("An error occurred while loading the page. Please try again.")
        print(f"Error in job_giver_dashboard: {e}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        # Don't reset the current page on error, just show the error
        st.stop()

def profile_section(job_giver):
    """Profile management section for job givers"""
    st.title("Company Profile")
    
    # Make sure we have a valid user_id in session state
    if not st.session_state.get('user_id'):
        st.error("Session expired. Please log in again.")
        # Clear session state to force re-login
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        return
    
    # Initialize job giver if it doesn't exist
    if not job_giver:
        try:
            job_giver = JobGiver.get_by_user_id(st.session_state.user_id)
            if not job_giver:
                # If we still can't get it, create a new instance
                job_giver = JobGiver(user_id=st.session_state.user_id)
        except Exception as e:
            print(f"Error loading job giver profile in profile_section: {e}")
            # Create a new instance as fallback
            job_giver = JobGiver(user_id=st.session_state.user_id)
    
    # Profile form
    with st.form("job_giver_profile_form"):
        company_name = st.text_input("Company Name", value=job_giver.company_name or "", key="jg_company_name")
        website = st.text_input("Website", value=job_giver.website or "", key="jg_website")
        location = st.text_input("Location", value=job_giver.location or "", key="jg_location")
        company_description = st.text_area("Company Description", 
                                          value=job_giver.company_description or "", 
                                          height=150,
                                          key="jg_company_description")
        
        submit_button = st.form_submit_button("Save Profile")
        
        if submit_button:
            # Process form data
            if not company_name:
                st.error("Company name is required")
                return
            
            # Update job giver object
            job_giver.company_name = company_name
            job_giver.company_description = company_description
            job_giver.website = website
            job_giver.location = location
            
            # Save to database
            if job_giver.update_profile():
                st.success("Profile updated successfully!")
            else:
                st.error("Failed to update profile. Please try again.")
    
    # Display current profile if complete
    if job_giver.profile_complete:
        st.subheader("Current Profile")
        
        st.write(f"**Company:** {job_giver.company_name}")
        st.write(f"**Website:** {job_giver.website}")
        st.write(f"**Location:** {job_giver.location}")
        
        if job_giver.company_description:
            st.write("**Company Description:**")
            st.write(job_giver.company_description)

def jobs_section(job_giver):
    """Jobs management section for job givers"""
    st.title("My Job Listings")
    
    # Debug info - print all session state keys at the start of jobs_section
    print("Session state keys at start of jobs_section:", list(st.session_state.keys()))
    print(f"User ID in session: {st.session_state.get('user_id')}")
    print(f"Username in session: {st.session_state.get('username')}")
    print(f"User type in session: {st.session_state.get('user_type')}")
    
    # Make sure we have a valid user_id in session state
    if not st.session_state.get('user_id'):
        print("No user_id in session state in jobs_section - redirecting to login")
        st.error("Session expired. Please log in again.")
        st.session_state.logged_in = False
        st.rerun()
        return
    
    # If job_giver is None, get it directly from the database
    if not job_giver:
        print("job_giver object is None in jobs_section, getting it directly")
        job_giver = JobGiver.get_by_user_id(st.session_state.user_id)
        
    # If we still don't have a job_giver, show an error
    if not job_giver:
        print("Failed to get job_giver from database")
        st.error("Unable to load your profile. Please try refreshing the page.")
        if st.button("Refresh Page"):
            st.rerun()
        return
    
    # Check if profile is complete
    if not job_giver.profile_complete or not job_giver.company_name:
        st.warning("Please complete your profile first before managing jobs.")
        if st.button("Go to Profile"):
            st.session_state.job_giver_current_page = "Profile"
            st.rerun()
        return

    # Check if job giver has enough credits to post a job
    try:
        if job_giver.credits < 1: 
            st.warning("You need at least 1 credit to post a job. Please purchase credits.")
            if st.button("Go to Credits", key="credits_button_jobs"):
                st.session_state.job_giver_current_page = "Credits"
                st.rerun()
            return
    except Exception as e:
        print(f"Error checking credits: {e}")
        st.error("Error checking your credits. Please refresh the page.")
        if st.button("Refresh Page"):
            st.rerun()
        return
    
    # Get existing jobs
    try:
        jobs = Job.get_by_job_giver_id(job_giver.id)
        if jobs is None:  # Handle case where get_by_job_giver_id returns None
            st.error("Error loading your jobs. Please try again.")
            return
    except Exception as e:
        st.error("Error loading your jobs. Please try again.")
        print(f"Error loading jobs: {e}")
        return
    
    # Create tabs for job management and applicants
    tab1, tab2 = st.tabs(["Manage Jobs", "View Applicants"])
    
    # Tab 1: Manage Jobs
    with tab1:
        # Add new job form
        with st.expander("Add New Job"):
            with st.form("new_job_form"):
                job_title = st.text_input("Job Title", key="job_title")
                
                col1, col2 = st.columns(2)
                with col1:
                    job_location = st.text_input("Job Location", key="job_location")
                with col2:
                    job_type = st.selectbox("Job Type", 
                                           ["Full-time", "Part-time", "Contract", "Internship", "Remote"],
                                           key="job_type")
                
                salary_range = st.text_input("Salary Range (e.g., $50,000 - $70,000)", key="salary_range")
                
                job_description = st.text_area("Job Description", height=150, key="job_description")
                
                # Requirements input (one per line)
                requirements_text = st.text_area("Requirements (one per line)", height=100, key="requirements_text")
                
                submit_button = st.form_submit_button("Post Job")
                
                if submit_button:
                    # Validate inputs
                    if not job_title or not job_description:
                        st.error("Job title and description are required")
                        return
                    
                    # Process requirements (split by newline and strip whitespace)
                    requirements = [req.strip() for req in requirements_text.split("\n") if req.strip()]
                    
                    # Create job object
                    job = Job(
                        job_giver_id=job_giver.id,
                        title=job_title,
                        description=job_description,
                        requirements=requirements,
                        location=job_location,
                        salary_range=salary_range,
                        job_type=job_type
                    )
                    
                    # Save to database
                    if job.create():
                        # Deduct credit
                        success, message = job_giver.use_credit()
                        if success:
                            st.success("Job posted successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to post job: {message}")
                    else:
                        st.error("Failed to post job. Please try again.")
        
        # Display existing jobs
        if jobs:
            for job in jobs:
                with st.expander(f"{job.title} ({job.active and 'Active' or 'Inactive'})"):
                    st.write(f"**Posted:** {job.created_at.strftime('%Y-%m-%d')}")
                    st.write(f"**Location:** {job.location}")
                    
                    if job.salary_range:
                        st.write(f"**Salary Range:** {job.salary_range}")
                    
                    st.write(f"**Job Type:** {job.job_type}")
                    
                    st.write("**Description:**")
                    st.write(job.description)
                    
                    if job.requirements:
                        st.write("**Requirements:**")
                        for req in job.requirements:
                            st.write(f"- {req}")
                    
                    # Toggle active status
                    if job.active:
                        if st.button(f"Deactivate Job", key=f"deactivate_{job.id}"):
                            if job.deactivate():
                                st.success("Job deactivated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to deactivate job. Please try again.")
                    else:
                        if st.button(f"Activate Job", key=f"activate_{job.id}"):
                            job.active = True
                            if job.update():
                                st.success("Job activated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to activate job. Please try again.")
        else:
            st.info("You haven't posted any jobs yet.")
    
    # Tab 2: View Applicants
    with tab2:
        if not jobs:
            st.info("You haven't posted any jobs yet.")
        else:
            # Create a dropdown to select a job
            job_titles = [f"{job.title} (ID: {job.id})" for job in jobs]
            selected_job_title = st.selectbox("Select a job to view applicants", job_titles)
            
            if selected_job_title:
                # Extract job ID from the selected title
                selected_job_id = int(selected_job_title.split("ID: ")[1].split(")")[0])

                # Ensure job_giver object is available and has an ID
                if not job_giver or not job_giver.id:
                    st.error("Job giver profile not loaded or incomplete. Cannot fetch applicants.")
                    return

                # Get potential applicants for the selected job using the new method
                potential_applicants = Job.get_potential_applicants(selected_job_id, job_giver.id)
                
                if potential_applicants:
                    st.write(f"### Applicants for {selected_job_title.split(' (ID:')[0]}")
                    st.write(f"Total interested candidates: {len(potential_applicants)}")
                    
                    # Prepare data for the summary DataFrame
                    applicant_data_for_df = []
                    for applicant in potential_applicants:
                        applicant_data_for_df.append({
                            "Name": applicant.applicant_name,
                            "Experience": f"{applicant.applicant_experience or 0} years",
                            "Location": applicant.applicant_location or "N/A",
                            "Applied On": applicant.application_date.strftime("%Y-%m-%d"),
                            "Status": applicant.match_status.capitalize() if applicant.is_matched else "Applied"
                        })
                    
                    if applicant_data_for_df:
                        df = pd.DataFrame(applicant_data_for_df)
                        st.dataframe(df, use_container_width=True)
                        
                        # Display detailed applicant information
                        st.write("### Applicant Details")
                        for i, applicant in enumerate(potential_applicants):
                            expander_title = f"{applicant.applicant_name} - Status: {applicant.match_status.capitalize() if applicant.is_matched else 'Applied'}"
                            with st.expander(expander_title):
                                st.write(f"**Applied On:** {applicant.application_date.strftime('%Y-%m-%d %H:%M')}")
                                st.write(f"**Experience:** {applicant.applicant_experience or 0} years")
                                st.write(f"**Location:** {applicant.applicant_location or 'N/A'}")
                                
                                if applicant.applicant_skills:
                                    st.write("**Skills:**")
                                    st.write(", ".join(applicant.applicant_skills))
                                
                                # Status management
                                st.write(f"**Current Status:** {applicant.match_status.capitalize()}")

                                if applicant.is_matched:
                                    st.write(f"**Matched On:** {applicant.match_created_at.strftime('%Y-%m-%d %H:%M') if applicant.match_created_at else 'N/A'}")
                                    st.write(f"**Email:** {applicant.applicant_email or 'N/A'}") # Show email for matched candidates

                                    if applicant.applicant_bio:
                                        st.write("**Bio:**")
                                        st.write(applicant.applicant_bio)
                                    
                                    if applicant.applicant_cv_path:
                                        st.write("**CV:**")
                                        try:
                                            if os.path.exists(applicant.applicant_cv_path):
                                                with open(applicant.applicant_cv_path, "rb") as file:
                                                    cv_filename = os.path.basename(applicant.applicant_cv_path)
                                                    st.download_button(
                                                        label="Download CV",
                                                        data=file,
                                                        file_name=cv_filename,
                                                        mime="application/pdf",
                                                        key=f"cv_dl_{applicant.job_seeker_id}_{selected_job_id}"
                                                    )
                                            else:
                                                st.error(f"CV file not found at {applicant.applicant_cv_path}")
                                        except Exception as e:
                                            st.error(f"Error loading CV file: {e}")
                                    else:
                                        st.write("CV not uploaded by candidate.")

                                    # Status update options for matched candidates
                                    match_status_options = ["active", "contacted", "interviewing", "hired", "rejected"]
                                    try:
                                        current_status_idx = match_status_options.index(applicant.match_status)
                                    except ValueError:
                                        current_status_idx = 0 # Default to 'active'

                                    new_match_status = st.selectbox(
                                        "Update Match Status",
                                        match_status_options,
                                        index=current_status_idx,
                                        key=f"match_status_select_{applicant.match_id}"
                                    )
                                    
                                    if new_match_status != applicant.match_status:
                                        if st.button("Update Status", key=f"update_match_status_btn_{applicant.match_id}"):
                                            if Match.update_status_by_id(applicant.match_id, new_match_status):
                                                st.success(f"Match status updated to {new_match_status.capitalize()}")
                                                st.rerun()
                                            else:
                                                st.error("Failed to update match status.")
                                else: # Candidate has applied but is not yet matched by this job giver
                                    st.write("**Bio (Preview):**")
                                    if applicant.applicant_bio:
                                        preview = applicant.applicant_bio[:150] + "..." if len(applicant.applicant_bio) > 150 else applicant.applicant_bio
                                        st.write(preview)
                                    else:
                                        st.write("No bio provided.")
                                    st.info("Full profile, CV, and contact details will be available upon a mutual match.")

                                    if st.button("👍 Express Interest & Match", key=f"match_cand_{applicant.job_seeker_id}_{selected_job_id}"):
                                        # This action is equivalent to the job giver swiping right on this candidate for this job
                                        jg_swipe = Swipe(
                                            user_id=st.session_state.user_id, # Job Giver's user_id
                                            target_id=applicant.job_seeker_id, # JobSeeker's ID from job_seekers table
                                            target_type="job_seeker",
                                            direction="right",
                                            job_id=selected_job_id
                                        )
                                        swipe_success, swipe_message = jg_swipe.create() # create() should handle match creation

                                        if swipe_success:
                                            if "match" in swipe_message.lower():
                                                st.balloons()
                                                st.success(f"It's a match with {applicant.applicant_name}! 🎉 Full details are now visible.")
                                            else: # Should be a match as seeker already swiped right
                                                st.info(swipe_message) # Fallback message
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to express interest: {swipe_message}")
                    else:
                        st.info("No applicant details to display in table.") # Should be caught by outer if
                else:
                    st.info("No candidates have expressed interest in this job yet.")

def candidates_section(job_giver):
    """Candidate swiping section for job givers"""
    st.title("Find Candidates for Your Jobs")
    
    # Make sure we have a valid user_id in session state
    if not st.session_state.get('user_id'):
        st.error("Session expired. Please log in again.")
        # Clear session state to force re-login
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        return
    
    # If job_giver is None, try to reload it from the database
    if not job_giver:
        try:
            job_giver = JobGiver.get_by_user_id(st.session_state.user_id)
            if not job_giver:
                st.error("Unable to load your profile. Please try refreshing the page.")
                if st.button("Refresh Page"):
                    st.rerun()
                return
        except Exception as e:
            print(f"Error loading job giver profile in candidates_section: {e}")
            st.error("An error occurred while loading your profile. Please try again.")
            if st.button("Refresh Page"):
                st.rerun()
            return

    # Check if job giver has enough credits
    try:
        if job_giver.credits < 10: # TODO: Replace '10' with dynamically fetched view_match_cost
            st.warning("You need at least 10 credits to match with candidates. Please purchase credits.")
            if st.button("Go to Credits", key="credits_button_candidates"):
                st.session_state.job_giver_current_page = "Credits"
                st.rerun()
            return
    except Exception as e:
        print(f"Error checking credits in candidates_section: {e}")
        st.error("Error checking your credits. Please refresh the page.")
        if st.button("Refresh Page"):
            st.rerun()
        return
    
    # Get existing jobs
    jobs = Job.get_by_job_giver_id(job_giver.id)
    
    if not jobs:
        st.warning("You need to post at least one job before you can match with candidates.")
        if st.button("Go to Jobs"):
            st.session_state.job_giver_current_page = "My Jobs"
            st.rerun()
        return
    
    # Filter for active jobs only
    active_jobs = [job for job in jobs if job.active]
    
    if not active_jobs:
        st.warning("You don't have any active jobs. Please activate a job before matching with candidates.")
        if st.button("Go to Jobs"):
            st.session_state.job_giver_menu = "My Jobs"
            st.rerun()
        return
    
    # Job selection
    st.subheader("Step 1: Select a Job to Find Candidates For")
    
    # Initialize selected job in session state if not present
    if "selected_job_for_candidates" not in st.session_state:
        st.session_state.selected_job_for_candidates = None
    
    # Create job selection options
    job_options = [f"{job.title} (ID: {job.id})" for job in active_jobs]
    selected_job_option = st.selectbox(
        "Select a job to find candidates for:",
        job_options,
        key="job_selection_for_candidates"
    )
    
    # Extract job ID from selection
    selected_job_id = int(selected_job_option.split("ID: ")[1].split(")")[0])
    
    # Find the selected job object
    selected_job = next((job for job in active_jobs if job.id == selected_job_id), None)
    
    if selected_job:
        st.session_state.selected_job_for_candidates = selected_job
        
        # Display selected job details
        st.write(f"**Selected Job:** {selected_job.title}")
        st.write(f"**Location:** {selected_job.location}")
        st.write(f"**Job Type:** {selected_job.job_type}")
        
        if selected_job.requirements:
            st.write("**Requirements:**")
            for req in selected_job.requirements:
                st.write(f"- {req}")
        
        st.subheader("Step 2: Find Candidates for This Job")
    
    # Search form
    with st.expander("Search Candidates", expanded=True):
        st.write("Filter candidates by your preferences:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            skills = st.text_input("Skills (comma-separated)", key="candidate_search_skills")
            min_experience = st.number_input("Minimum Years of Experience", min_value=0, value=0, key="candidate_search_experience")
        
        with col2:
            location = st.text_input("Location", key="candidate_search_location")
            education = st.text_input("Education", key="candidate_search_education")
        
        # Button row for search and reset
        col1, col2 = st.columns(2)
        
        with col1:
            # Store search parameters in session state
            if st.button("Search", key="candidate_search_button"):
                st.session_state.candidate_search_params = {
                    "skills": skills if skills.strip() else None,
                    "min_experience": min_experience if min_experience > 0 else None,
                    "location": location if location.strip() else None,
                    "education": education if education.strip() else None
                }
                # Reset candidate index when search parameters change
                st.session_state.candidate_index = 0
                st.success("Search filters applied!")
        
        with col2:
            # Reset filters button
            if st.button("Reset Filters", key="reset_filters_button"):
                # Clear search parameters
                st.session_state.candidate_search_params = {
                    "skills": None,
                    "min_experience": None,
                    "location": None,
                    "education": None
                }
                # Reset candidate index
                st.session_state.candidate_index = 0
                
                # Reset left swipes to make previously swiped candidates available again
                job_id = st.session_state.selected_job_for_candidates.id if st.session_state.selected_job_for_candidates else None
                success, message = Swipe.reset_left_swipes(st.session_state.user_id, 'job_seeker', job_id)
                
                if success:
                    st.success(f"Filters have been reset! {message.split(':')[0]}. All unmatched candidates are now available.")
                else:
                    st.warning("Filters have been reset, but there was an issue resetting swipe history.")
                    print(f"Error resetting swipes: {message}")
    
    # Initialize search params in session state if not present
    if "candidate_search_params" not in st.session_state:
        st.session_state.candidate_search_params = {
            "skills": None,
            "min_experience": None,
            "location": None,
            "education": None
        }
    
    # Ensure all parameters are properly set to None if they're empty strings
    if st.session_state.candidate_search_params["skills"] == "":
        st.session_state.candidate_search_params["skills"] = None
    if st.session_state.candidate_search_params["location"] == "":
        st.session_state.candidate_search_params["location"] = None
    if st.session_state.candidate_search_params["education"] == "":
        st.session_state.candidate_search_params["education"] = None
    
    # Only proceed if a job is selected
    if not st.session_state.selected_job_for_candidates:
        st.warning("Please select a job first to find candidates.")
        return
        
    # Get candidates for swiping with search parameters
    candidates = JobSeeker.get_all_for_swiping(
        job_giver.id, 
        limit=50,  # Increased limit to show more candidates
        skills=st.session_state.candidate_search_params["skills"],
        min_experience=st.session_state.candidate_search_params["min_experience"],
        location=st.session_state.candidate_search_params["location"],
        education=st.session_state.candidate_search_params["education"],
        job_id=st.session_state.selected_job_for_candidates.id  # Pass the specific job ID
    )
    
    if not candidates:
        st.info("No candidates match your search criteria. Try adjusting your filters or reset to see previously skipped candidates.")
        
        # Add a button to reset left swipes
        if st.button("Show Previously Skipped Candidates", key="reset_skipped_candidates"):
            job_id = st.session_state.selected_job_for_candidates.id if st.session_state.selected_job_for_candidates else None
            success, message = Swipe.reset_left_swipes(st.session_state.user_id, 'job_seeker', job_id)
            if success:
                st.success(f"{message.split(':')[0]}. Previously skipped candidates are now available.")
                st.rerun()
            else:
                st.warning("There was an issue resetting your swipe history.")
                print(f"Error resetting swipes: {message}")
        return
    
    # Initialize candidate index in session state if not present
    if "candidate_index" not in st.session_state:
        st.session_state.candidate_index = 0
    
    # Get current candidate
    if st.session_state.candidate_index < len(candidates):
        current_candidate = candidates[st.session_state.candidate_index]
        
        # Display candidate card
        with st.container():
            st.subheader(current_candidate.full_name)
            st.write(f"**Considering for:** {st.session_state.selected_job_for_candidates.title}")
            st.write(f"**Location:** {current_candidate.location}")
            st.write(f"**Experience:** {current_candidate.experience} years")
            
            if current_candidate.education:
                st.write(f"**Education:** {current_candidate.education}")
            
            if current_candidate.skills:
                st.write("**Skills:**")
                st.write(", ".join(current_candidate.skills))
            
            # Only show partial profile until match
            st.write("**Bio (Preview):**")
            if current_candidate.bio:
                # Show only first 100 characters of bio
                preview = current_candidate.bio[:100] + "..." if len(current_candidate.bio) > 100 else current_candidate.bio
                st.write(preview)
            else:
                st.write("No bio provided.")
            
            st.info("Swipe right to see full profile and CV upon matching.")
        
        # Swipe buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("👎 Lets see some more", key="swipe_left"):
                # Record left swipe
                swipe = Swipe(
                    user_id=st.session_state.user_id,
                    target_id=current_candidate.id,
                    target_type="job_seeker",
                    direction="left",
                    job_id=st.session_state.selected_job_for_candidates.id
                )
                success, message = swipe.create()
                
                # Move to next candidate
                st.session_state.candidate_index += 1
                st.rerun()
        
        with col2:
            if st.button("👍 Match Please", key="swipe_right"):
                # Record right swipe
                swipe = Swipe(
                    user_id=st.session_state.user_id,
                    target_id=current_candidate.id,
                    target_type="job_seeker",
                    direction="right",
                    job_id=st.session_state.selected_job_for_candidates.id
                )
                success, message = swipe.create()
                
                # Move to next candidate
                st.session_state.candidate_index += 1
                
                if success and "match" in message.lower():
                    st.balloons()
                    job_title = st.session_state.selected_job_for_candidates.title
                    st.success(f"It's a match for '{job_title}'! 🎉 Check your matches tab.")
                
                # Get the next set of candidates if we've reached the end
                if st.session_state.candidate_index >= len(candidates):
                    # Get a fresh set of candidates
                    new_candidates = JobSeeker.get_all_for_swiping(
                        job_giver.id, 
                        limit=50,  # Increased limit to show more candidates
                        skills=st.session_state.candidate_search_params["skills"],
                        min_experience=st.session_state.candidate_search_params["min_experience"],
                        location=st.session_state.candidate_search_params["location"],
                        education=st.session_state.candidate_search_params["education"],
                        job_id=st.session_state.selected_job_for_candidates.id  # Pass the specific job ID
                    )
                    
                    if not new_candidates:
                        st.session_state.candidate_index = 0
                    
                st.rerun()
    else:
        st.info("You've seen all available candidates matching your current filters.")
        # Reset index for next time
        st.session_state.candidate_index = 0
        
        # Add a button to reset left swipes
        if st.button("Show Previously Skipped Candidates", key="end_reset_skipped_candidates"):
            job_id = st.session_state.selected_job_for_candidates.id if st.session_state.selected_job_for_candidates else None
            success, message = Swipe.reset_left_swipes(st.session_state.user_id, 'job_seeker', job_id)
            if success:
                st.success(f"{message.split(':')[0]}. Previously skipped candidates are now available.")
                st.rerun()
            else:
                st.warning("There was an issue resetting your swipe history.")
                print(f"Error resetting swipes: {message}")

def matches_section(job_giver):
    """Matches section for job givers"""
    st.title("My Matches")
    
    # Make sure we have a valid user_id in session state
    if not st.session_state.get('user_id'):
        st.error("Session expired. Please log in again.")
        # Clear session state to force re-login
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        return
    
    # If job_giver is None, try to reload it from the database
    if not job_giver:
        try:
            job_giver = JobGiver.get_by_user_id(st.session_state.user_id)
            if not job_giver:
                st.error("Unable to load your profile. Please try refreshing the page.")
                if st.button("Refresh Page"):
                    st.rerun()
                return
        except Exception as e:
            print(f"Error loading job giver profile in matches_section: {e}")
            st.error("An error occurred while loading your profile. Please try again.")
            if st.button("Refresh Page"):
                st.rerun()
            return
    
    # Debug info
    print(f"Fetching matches for job giver ID: {job_giver.id}")
    
    # Get matches for job giver
    matches = Match.get_for_job_giver(job_giver.id)
    
    # More debug info
    print(f"Retrieved {len(matches)} matches for job giver")
    
    if not matches:
        st.info("You don't have any matches yet. Start swiping to find candidates!")
        return
    
    # Display matches
    for match in matches:
        with st.expander(f"{match.job_seeker_name} - {match.job_title}"):
            st.write(f"**Matched on:** {match.created_at.strftime('%Y-%m-%d')}")
            st.write(f"**Status:** {match.status.capitalize()}")
            
            # Get job seeker details (full profile now visible)
            conn = get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT js.full_name, js.bio, js.skills, js.experience, 
                               js.education, js.location, js.cv_path,
                               u.email
                        FROM job_seekers js
                        JOIN users u ON js.user_id = u.id
                        WHERE js.id = %s
                    """, (match.job_seeker_id,))
                    
                    seeker_data = cursor.fetchone()
                    if seeker_data:
                        name, bio, skills, experience, education, location, cv_path, email = seeker_data
                        
                        st.write(f"**Name:** {name}")
                        st.write(f"**Email:** {email}")
                        st.write(f"**Location:** {location}")
                        st.write(f"**Experience:** {experience} years")
                        
                        if education:
                            st.write(f"**Education:** {education}")
                        
                        if skills:
                            st.write("**Skills:**")
                            st.write(", ".join(skills))
                        
                        if bio:
                            st.write("**Bio:**")
                            st.write(bio)
                        
                        if cv_path:
                            st.write("**CV is available**")
                            # Create a download button for the CV
                            try:
                                if os.path.exists(cv_path):
                                    with open(cv_path, "rb") as file:
                                        cv_filename = os.path.basename(cv_path)
                                        st.download_button(
                                            label="Download CV",
                                            data=file,
                                            file_name=cv_filename,
                                            mime="application/pdf"
                                        )
                                else:
                                    st.error(f"CV file not found at {cv_path}")
                            except Exception as e:
                                st.error(f"Error loading CV file: {e}")
                except Exception as e:
                    st.error(f"Error retrieving candidate details: {e}")
                finally:
                    cursor.close()
                    conn.close()

def credits_section(job_giver):
    """Credits section for job givers"""
    st.title("Credits")
    
    # Make sure we have a valid user_id in session state
    if not st.session_state.get('user_id'):
        st.error("Session expired. Please log in again.")
        # Clear session state to force re-login
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        return
    
    # If job_giver is None, try to reload it from the database
    if not job_giver:
        try:
            job_giver = JobGiver.get_by_user_id(st.session_state.user_id)
            if not job_giver:
                st.error("Unable to load your profile. Please try refreshing the page.")
                if st.button("Refresh Page"):
                    st.rerun()
                return
        except Exception as e:
            print(f"Error loading job giver profile in credits_section: {e}")
            st.error("An error occurred while loading your profile. Please try again.")
            if st.button("Refresh Page"):
                st.rerun()
            return
    
    # Display current credit balance
    st.header(f"Current Balance: {job_giver.credits} credits")
    
    st.subheader("Purchase Credits")

    active_packages = CreditPackage.get_all_active_sorted()

    if not active_packages:
        st.info("No credit packages are currently available for purchase.")
    else:
        # Dynamically create columns based on number of packages, max 3 per row
        num_packages = len(active_packages)
        cols_per_row = min(num_packages, 3)
        
        for i in range(0, num_packages, cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < num_packages:
                    package = active_packages[i+j]
                    with cols[j]:
                        st.markdown(f"#### {package.name}")
                        if package.description:
                            st.caption(package.description)
                        st.markdown(f"**{package.credits_amount} Credits**")
                        st.markdown(f"### INR {package.price_inr:.2f}")
                        if st.button(f"Buy {package.name}", key=f"buy_package_{package.id}"):
                            if job_giver.add_credits(package.credits_amount):
                                st.success(f"Successfully purchased {package.credits_amount} credits from {package.name} package!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("Failed to purchase credits. Please try again.")
    
    # # Custom amount
    # st.write("**Custom Amount**")
    # custom_amount = st.number_input("Number of Credits", min_value=1, value=10, step=1, key="custom_credit_amount")
    # custom_price = custom_amount * 2  # $2 per credit
    # 
    # if st.button(f"Buy {custom_amount} Credits for ${custom_price}", key="buy_custom_credits"):
    #     if job_giver.add_credits(custom_amount):
    #         st.success(f"Successfully purchased {custom_amount} credits!")
    #         st.balloons()
    #         st.rerun()
    #     else:
    #         st.error("Failed to purchase credits. Please try again.")
    
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