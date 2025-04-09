#!/usr/bin/env python3

"""
AI Job Applicant Bot - Streamlit Dashboard

The main UI for the job application bot using Streamlit.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
from typing import Dict, List, Any, Optional, Union

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from resume.parser import ResumeParser, get_resume_files
from resume.matcher import JobMatcher
from automation.job_search import JobSearchManager, JobPost
from automation.applicator import ApplicationAutomator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Job Applicant Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if 'resume_parser' not in st.session_state:
    st.session_state.resume_parser = None
if 'job_search_manager' not in st.session_state:
    st.session_state.job_search_manager = None
if 'job_matcher' not in st.session_state:
    st.session_state.job_matcher = None
if 'config' not in st.session_state:
    st.session_state.config = None


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        st.error(f"Error loading configuration: {e}")
        return {}


def initialize_session(config_path: str):
    """Initialize the session with configuration"""
    if st.session_state.config is None:
        # Load configuration
        config = load_config(config_path)
        if not config:
            st.error("Failed to load configuration. Please check the config file.")
            return False
        
        st.session_state.config = config
    
    # Load resume
    if st.session_state.resume_parser is None:
        resume_files = get_resume_files()
        if not resume_files:
            st.warning("No resume files found. Please upload a resume file (PDF, DOCX, or TXT) to the resume/data directory.")
            return False
        
        try:
            st.session_state.resume_parser = ResumeParser(resume_files[0])
            logger.info(f"Loaded resume: {resume_files[0]}")
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            st.error(f"Error parsing resume: {e}")
            return False
    
    # Initialize job search manager
    if st.session_state.job_search_manager is None:
        st.session_state.job_search_manager = JobSearchManager(st.session_state.config)
        logger.info("Initialized job search manager")
    
    # Initialize job matcher
    if st.session_state.job_matcher is None and st.session_state.resume_parser is not None:
        st.session_state.job_matcher = JobMatcher(st.session_state.resume_parser)
        logger.info("Initialized job matcher")
    
    return True


def search_jobs():
    """Search for jobs across all enabled job boards"""
    with st.spinner("Searching for jobs..."):
        try:
            new_jobs = st.session_state.job_search_manager.search_all_job_boards()
            
            if new_jobs:
                st.success(f"Found {len(new_jobs)} new jobs!")
            else:
                st.info("No new jobs found.")
                
            # Return all jobs, including previously found ones
            return st.session_state.job_search_manager.get_all_jobs()
        except Exception as e:
            logger.error(f"Error searching for jobs: {e}")
            st.error(f"Error searching for jobs: {e}")
            return []


def match_jobs(jobs: List[JobPost]):
    """Match jobs to resume and calculate scores"""
    with st.spinner("Matching jobs to your resume..."):
        try:
            for job in jobs:
                if job.match_score == 0:  # Only match if not already matched
                    match_result = st.session_state.job_matcher.match_job(job.description)
                    job.match_score = match_result['overall_score']
                    
                    # Update in the database
                    st.session_state.job_search_manager.update_job_match_score(
                        job.id, match_result['overall_score']
                    )
            
            st.success("Jobs matched successfully!")
            return sorted(jobs, key=lambda j: j.match_score, reverse=True)
        except Exception as e:
            logger.error(f"Error matching jobs: {e}")
            st.error(f"Error matching jobs: {e}")
            return jobs


def apply_to_jobs(jobs: List[JobPost], limit: int):
    """Apply to selected jobs"""
    with st.spinner(f"Applying to up to {limit} jobs..."):
        try:
            # Filter jobs that haven't been applied to yet
            jobs_to_apply = [job for job in jobs if job.status == "New"][:limit]
            
            if not jobs_to_apply:
                st.info("No new jobs to apply to.")
                return []
            
            with ApplicationAutomator(st.session_state.config, st.session_state.resume_parser) as automator:
                results = automator.apply_to_jobs(jobs_to_apply, limit=limit)
                
                # Update job statuses
                for result in results:
                    if result['success']:
                        st.session_state.job_search_manager.update_job_status(
                            result['job_id'], "Applied", f"Applied on {result['timestamp']}"
                        )
                    else:
                        st.session_state.job_search_manager.update_job_status(
                            result['job_id'], "Failed", f"Failed to apply on {result['timestamp']}: {result.get('error', 'Unknown error')}"
                        )
                
                success_count = sum(1 for r in results if r['success'])
                if success_count > 0:
                    st.success(f"Successfully applied to {success_count} jobs!")
                else:
                    st.warning("Failed to apply to any jobs. Check the logs for details.")
                
                # Save results to file for reference
                automator.save_application_results()
                
                return results
        except Exception as e:
            logger.error(f"Error applying to jobs: {e}")
            st.error(f"Error applying to jobs: {e}")
            return []


def display_dashboard():
    """Display the main dashboard"""
    st.title("🤖 AI Job Applicant Bot")
    
    # Main action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Search for Jobs", use_container_width=True):
            st.session_state.jobs = search_jobs()
    
    with col2:
        if st.button("⚖️ Match Jobs to Resume", use_container_width=True):
            if hasattr(st.session_state, 'jobs') and st.session_state.jobs:
                st.session_state.jobs = match_jobs(st.session_state.jobs)
            else:
                st.warning("No jobs found. Please search for jobs first.")
    
    with col3:
        apply_limit = st.number_input("Application Limit", min_value=1, max_value=20, value=3)
        if st.button("🚀 Apply to Top Jobs", use_container_width=True):
            if hasattr(st.session_state, 'jobs') and st.session_state.jobs:
                # Sort by match score and apply to top matches
                sorted_jobs = sorted(st.session_state.jobs, key=lambda j: j.match_score, reverse=True)
                apply_to_jobs(sorted_jobs, apply_limit)
            else:
                st.warning("No jobs found. Please search for jobs first.")
    
    # Display job statistics
    if hasattr(st.session_state, 'jobs') and st.session_state.jobs:
        st.subheader("Job Statistics")
        
        total_jobs = len(st.session_state.jobs)
        new_jobs = sum(1 for job in st.session_state.jobs if job.status == "New")
        applied_jobs = sum(1 for job in st.session_state.jobs if job.status == "Applied")
        failed_jobs = sum(1 for job in st.session_state.jobs if job.status == "Failed")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Jobs", total_jobs)
        col2.metric("New Jobs", new_jobs)
        col3.metric("Applied", applied_jobs)
        col4.metric("Failed", failed_jobs)
        
        # Create a DataFrame for easier visualization
        job_data = []
        for job in st.session_state.jobs:
            job_data.append({
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "job_board": job.job_board,
                "match_score": job.match_score,
                "status": job.status,
                "url": job.url
            })
        
        if job_data:
            df = pd.DataFrame(job_data)
            
            # Create a stacked bar chart of jobs by status and job board
            status_counts = df.groupby(['job_board', 'status']).size().reset_index(name='count')
            fig = px.bar(status_counts, x='job_board', y='count', color='status',
                         title='Jobs by Source and Status',
                         labels={'job_board': 'Job Board', 'count': 'Number of Jobs', 'status': 'Status'})
            st.plotly_chart(fig)
        
        # Display job table
        st.subheader("All Jobs")
        
        # Add viewing options
        status_filter = st.multiselect("Filter by Status", ["New", "Applied", "Failed"], default=["New"])
        sort_by = st.selectbox("Sort by", ["Match Score", "Title", "Company", "Job Board"])
        
        # Filter and sort the DataFrame
        df_filtered = df[df['status'].isin(status_filter)]
        
        if sort_by == "Match Score":
            df_filtered = df_filtered.sort_values(by='match_score', ascending=False)
        elif sort_by == "Title":
            df_filtered = df_filtered.sort_values(by='title')
        elif sort_by == "Company":
            df_filtered = df_filtered.sort_values(by='company')
        elif sort_by == "Job Board":
            df_filtered = df_filtered.sort_values(by='job_board')
        
        # Create a clickable link column
        df_filtered['link'] = df_filtered['url'].apply(lambda x: f'<a href="{x}" target="_blank">View</a>')
        
        # Format the match score as a percentage
        df_filtered['match_score'] = df_filtered['match_score'].apply(lambda x: f"{x:.1f}%")
        
        # Display the table with clickable links
        st.write(df_filtered[['title', 'company', 'location', 'job_board', 'match_score', 'status', 'link']].to_html(escape=False), unsafe_allow_html=True)
    
    else:
        st.info("No jobs found yet. Click 'Search for Jobs' to start.")


def display_resume_view():
    """Display resume information and skills"""
    st.title("📄 Resume")
    
    if st.session_state.resume_parser:
        resume_data = st.session_state.resume_parser.get_parsed_data()
        
        # Display basic information
        st.subheader("Personal Information")
        
        contact_info = resume_data['contact_info']
        st.write(f"**Name:** {contact_info.get('name', 'Not found')}")
        st.write(f"**Email:** {contact_info.get('email', 'Not found')}")
        st.write(f"**Phone:** {contact_info.get('phone', 'Not found')}")
        st.write(f"**Location:** {contact_info.get('location', 'Not found')}")
        
        if contact_info.get('linkedin'):
            st.write(f"**LinkedIn:** [{contact_info.get('linkedin')}]({contact_info.get('linkedin')})")
        
        if contact_info.get('github'):
            st.write(f"**GitHub:** [{contact_info.get('github')}]({contact_info.get('github')})")
        
        # Display skills
        st.subheader("Skills")
        
        skills = resume_data.get('skills', [])
        if skills:
            # Create columns for skills
            cols = st.columns(3)
            for i, skill in enumerate(skills):
                cols[i % 3].write(f"- {skill}")
        else:
            st.write("No skills found in resume.")
        
        # Display experience
        st.subheader("Experience")
        
        experience = resume_data.get('experience', [])
        if experience:
            for exp in experience:
                st.write(f"**{exp.get('position', 'Position')}** at {exp.get('company', 'Company')}")
                st.write(f"{exp.get('start_date', '')} - {exp.get('end_date', '')}")
                st.write(exp.get('description', ''))
                st.write("---")
        else:
            st.write("No experience found in resume.")
        
        # Display education
        st.subheader("Education")
        
        education = resume_data.get('education', [])
        if education:
            for edu in education:
                st.write(f"**{edu.get('degree', 'Degree')}** from {edu.get('institution', 'Institution')}")
                if edu.get('graduation_date'):
                    st.write(f"Graduated: {edu.get('graduation_date')}")
                if edu.get('major'):
                    st.write(f"Major: {edu.get('major')}")
                st.write("---")
        else:
            st.write("No education found in resume.")
        
        # Display summary
        if resume_data.get('summary'):
            st.subheader("Summary")
            st.write(resume_data.get('summary'))
    
    else:
        st.warning("No resume found. Please upload a resume file to the resume/data directory.")


def display_settings():
    """Display and update settings"""
    st.title("⚙️ Settings")
    
    if st.session_state.config:
        config = st.session_state.config
        
        st.subheader("User Information")
        
        with st.form("user_info_form"):
            name = st.text_input("Name", value=config['user'].get('name', ''))
            email = st.text_input("Email", value=config['user'].get('email', ''))
            phone = st.text_input("Phone", value=config['user'].get('phone', ''))
            location = st.text_input("Location", value=config['user'].get('location', ''))
            linkedin = st.text_input("LinkedIn URL", value=config['user'].get('linkedin', ''))
            github = st.text_input("GitHub URL", value=config['user'].get('github', ''))
            
            if st.form_submit_button("Update User Information"):
                config['user'] = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'location': location,
                    'linkedin': linkedin,
                    'github': github
                }
                
                try:
                    with open('config/config.json', 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    st.success("User information updated successfully!")
                    
                    # Reload the configuration
                    st.session_state.config = load_config('config/config.json')
                except Exception as e:
                    logger.error(f"Error updating user information: {e}")
                    st.error(f"Error updating user information: {e}")
        
        st.subheader("Job Search Settings")
        
        with st.form("job_search_form"):
            # Job titles
            job_titles = st.text_area("Job Titles (one per line)", 
                                      value='\n'.join(config['job_search'].get('titles', [])))
            
            # Remote only
            remote_only = st.checkbox("Remote Only", 
                                     value=config['job_search'].get('remote_only', True))
            
            # Excluded keywords
            excluded_keywords = st.text_area("Excluded Keywords (one per line)", 
                                           value='\n'.join(config['job_search'].get('exclude_keywords', [])))
            
            # Min salary
            min_salary = st.number_input("Minimum Salary", 
                                       value=config['job_search'].get('min_salary', 0),
                                       step=5000)
            
            if st.form_submit_button("Update Job Search Settings"):
                config['job_search'] = {
                    'titles': [title.strip() for title in job_titles.split('\n') if title.strip()],
                    'remote_only': remote_only,
                    'locations': ["Remote"] if remote_only else [],
                    'exclude_keywords': [kw.strip() for kw in excluded_keywords.split('\n') if kw.strip()],
                    'min_salary': min_salary
                }
                
                try:
                    with open('config/config.json', 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    st.success("Job search settings updated successfully!")
                    
                    # Reload the configuration and reset the job search manager
                    st.session_state.config = load_config('config/config.json')
                    st.session_state.job_search_manager = JobSearchManager(st.session_state.config)
                except Exception as e:
                    logger.error(f"Error updating job search settings: {e}")
                    st.error(f"Error updating job search settings: {e}")
        
        st.subheader("Application Settings")
        
        with st.form("application_form"):
            # Auto submit
            auto_submit = st.checkbox("Auto Submit Applications", 
                                    value=config['application'].get('auto_submit', False))
            
            # Application limit per day
            app_limit = st.number_input("Application Limit Per Day", 
                                       min_value=1, max_value=50,
                                       value=config['application'].get('application_limit_per_day', 10))
            
            if st.form_submit_button("Update Application Settings"):
                config['application'] = {
                    'auto_submit': auto_submit,
                    'application_limit_per_day': app_limit
                }
                
                try:
                    with open('config/config.json', 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    st.success("Application settings updated successfully!")
                    
                    # Reload the configuration
                    st.session_state.config = load_config('config/config.json')
                except Exception as e:
                    logger.error(f"Error updating application settings: {e}")
                    st.error(f"Error updating application settings: {e}")
        
        st.subheader("Job Board Settings")
        
        with st.form("job_board_form"):
            # LinkedIn
            st.write("**LinkedIn**")
            linkedin_enabled = st.checkbox("Enable LinkedIn", 
                                         value=config['job_boards'].get('linkedin', {}).get('enabled', False))
            linkedin_username = st.text_input("LinkedIn Username", 
                                           value=config['job_boards'].get('linkedin', {}).get('username', ''))
            linkedin_password = st.text_input("LinkedIn Password", 
                                           value=config['job_boards'].get('linkedin', {}).get('password', ''),
                                           type="password")
            
            st.write("---")
            
            # Indeed
            st.write("**Indeed**")
            indeed_enabled = st.checkbox("Enable Indeed", 
                                       value=config['job_boards'].get('indeed', {}).get('enabled', False))
            indeed_username = st.text_input("Indeed Username", 
                                         value=config['job_boards'].get('indeed', {}).get('username', ''))
            indeed_password = st.text_input("Indeed Password", 
                                         value=config['job_boards'].get('indeed', {}).get('password', ''),
                                         type="password")
            
            st.write("---")
            
            # Dice
            st.write("**Dice**")
            dice_enabled = st.checkbox("Enable Dice", 
                                     value=config['job_boards'].get('dice', {}).get('enabled', False))
            
            st.write("---")
            
            # RemoteOK
            st.write("**RemoteOK**")
            remoteok_enabled = st.checkbox("Enable RemoteOK", 
                                        value=config['job_boards'].get('remoteok', {}).get('enabled', False))
            
            st.write("---")
            
            # AngelList
            st.write("**AngelList**")
            angellist_enabled = st.checkbox("Enable AngelList", 
                                         value=config['job_boards'].get('angellist', {}).get('enabled', False))
            angellist_username = st.text_input("AngelList Username", 
                                            value=config['job_boards'].get('angellist', {}).get('username', ''))
            angellist_password = st.text_input("AngelList Password", 
                                            value=config['job_boards'].get('angellist', {}).get('password', ''),
                                            type="password")
            
            if st.form_submit_button("Update Job Board Settings"):
                config['job_boards'] = {
                    'linkedin': {
                        'enabled': linkedin_enabled,
                        'username': linkedin_username,
                        'password': linkedin_password
                    },
                    'indeed': {
                        'enabled': indeed_enabled,
                        'username': indeed_username,
                        'password': indeed_password
                    },
                    'dice': {
                        'enabled': dice_enabled
                    },
                    'remoteok': {
                        'enabled': remoteok_enabled
                    },
                    'angellist': {
                        'enabled': angellist_enabled,
                        'username': angellist_username,
                        'password': angellist_password
                    }
                }
                
                try:
                    with open('config/config.json', 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    st.success("Job board settings updated successfully!")
                    
                    # Reload the configuration and reset the job search manager
                    st.session_state.config = load_config('config/config.json')
                    st.session_state.job_search_manager = JobSearchManager(st.session_state.config)
                except Exception as e:
                    logger.error(f"Error updating job board settings: {e}")
                    st.error(f"Error updating job board settings: {e}")
    
    else:
        st.warning("Configuration not loaded. Please check the config file.")


def main():
    """Main entry point for the Streamlit app"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='AI Job Applicant Bot UI')
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file')
    args = parser.parse_args()
    
    # Initialize the session
    if not initialize_session(args.config):
        return
    
    # Setup sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Resume", "Settings"])
    
    # Display the selected page
    if page == "Dashboard":
        display_dashboard()
    elif page == "Resume":
        display_resume_view()
    elif page == "Settings":
        display_settings()
    
    # Display footer
    st.sidebar.markdown("---")
    st.sidebar.info("AI Job Applicant Bot - v1.0.0")
    st.sidebar.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
