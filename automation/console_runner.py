#!/usr/bin/env python3

"""
Console Runner

Provides command-line interface for running the job application bot without the UI.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

from automation.job_search import JobSearchManager, JobPost
from automation.applicator import ApplicationAutomator
from resume.parser import ResumeParser, get_resume_files
from resume.matcher import JobMatcher

logger = logging.getLogger(__name__)

class ConsoleApplication:
    """Manages the console-based application flow"""
    
    def __init__(self, config_path: str):
        """
        Initialize the console application
        
        Args:
            config_path: Path to config file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.resume_parser = None
        self.job_search_manager = None
        self.job_matcher = None
        
        # Check if configuration loaded successfully
        if not self.config:
            logger.error(f"Failed to load configuration from {config_path}")
            sys.exit(1)
        
        # Initialize components
        self._initialize_components()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def _initialize_components(self):
        """Initialize all required components"""
        # Load resume
        resume_files = get_resume_files()
        if not resume_files:
            logger.error("No resume files found. Please add a resume to the resume/data directory.")
            sys.exit(1)
        
        try:
            self.resume_parser = ResumeParser(resume_files[0])
            logger.info(f"Loaded resume: {resume_files[0]}")
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            sys.exit(1)
        
        # Initialize job search manager
        self.job_search_manager = JobSearchManager(self.config)
        logger.info("Initialized job search manager")
        
        # Initialize job matcher
        self.job_matcher = JobMatcher(self.resume_parser)
        logger.info("Initialized job matcher")
    
    def search_jobs(self) -> List[JobPost]:
        """
        Search for jobs across all enabled job boards
        
        Returns:
            List of JobPost objects
        """
        logger.info("Searching for jobs...")
        
        try:
            new_jobs = self.job_search_manager.search_all_job_boards()
            
            if new_jobs:
                logger.info(f"Found {len(new_jobs)} new jobs")
            else:
                logger.info("No new jobs found")
                
            # Return all jobs, including previously found ones
            all_jobs = self.job_search_manager.get_all_jobs()
            logger.info(f"Total jobs in database: {len(all_jobs)}")
            
            return all_jobs
        except Exception as e:
            logger.error(f"Error searching for jobs: {e}")
            return []
    
    def match_jobs(self, jobs: List[JobPost]) -> List[JobPost]:
        """
        Match jobs to resume and calculate scores
        
        Args:
            jobs: List of JobPost objects to match
            
        Returns:
            List of matched JobPost objects
        """
        logger.info("Matching jobs to resume...")
        
        try:
            matched_count = 0
            
            for job in jobs:
                if job.match_score == 0:  # Only match if not already matched
                    match_result = self.job_matcher.match_job(job.description)
                    job.match_score = match_result['overall_score']
                    
                    # Update in the database
                    self.job_search_manager.update_job_match_score(
                        job.id, match_result['overall_score']
                    )
                    
                    matched_count += 1
                    
                    # Log some details about the match
                    logger.info(f"Matched job: {job.title} at {job.company} - Score: {job.match_score:.1f}%")
                    logger.info(f"  Matching skills: {', '.join(match_result['matching_skills'][:5])}")
                    
                    if match_result['missing_skills']:
                        logger.info(f"  Missing skills: {', '.join(match_result['missing_skills'][:5])}")
            
            logger.info(f"Matched {matched_count} new jobs")
            
            # Sort by match score
            return sorted(jobs, key=lambda j: j.match_score, reverse=True)
        except Exception as e:
            logger.error(f"Error matching jobs: {e}")
            return jobs
    
    def apply_to_jobs(self, jobs: List[JobPost], limit: int) -> List[Dict[str, Any]]:
        """
        Apply to jobs up to the specified limit
        
        Args:
            jobs: List of JobPost objects to apply to
            limit: Maximum number of jobs to apply to
            
        Returns:
            List of application results
        """
        logger.info(f"Applying to up to {limit} jobs...")
        
        try:
            # Filter jobs that haven't been applied to yet
            jobs_to_apply = [job for job in jobs if job.status == "New"][:limit]
            
            if not jobs_to_apply:
                logger.info("No new jobs to apply to")
                return []
            
            logger.info(f"Found {len(jobs_to_apply)} jobs to apply to")
            
            with ApplicationAutomator(self.config, self.resume_parser) as automator:
                results = automator.apply_to_jobs(jobs_to_apply, limit=limit)
                
                # Update job statuses
                for result in results:
                    if result['success']:
                        self.job_search_manager.update_job_status(
                            result['job_id'], "Applied", f"Applied on {result['timestamp']}"
                        )
                        logger.info(f"Successfully applied to {result['job_title']} at {result['company']}")
                    else:
                        self.job_search_manager.update_job_status(
                            result['job_id'], "Failed", f"Failed to apply on {result['timestamp']}: {result.get('error', 'Unknown error')}"
                        )
                        logger.warning(f"Failed to apply to {result['job_title']} at {result['company']}: {result.get('error', 'Unknown error')}")
                
                # Save results to file for reference
                automator.save_application_results()
                
                success_count = sum(1 for r in results if r['success'])
                logger.info(f"Successfully applied to {success_count} out of {len(results)} jobs")
                
                return results
        except Exception as e:
            logger.error(f"Error applying to jobs: {e}")
            return []
    
    def display_jobs(self, jobs: List[JobPost], limit: Optional[int] = None):
        """
        Display jobs in a formatted table
        
        Args:
            jobs: List of JobPost objects to display
            limit: Maximum number of jobs to display (optional)
        """
        if not jobs:
            print("No jobs found")
            return
        
        # Limit the number of jobs to display if specified
        if limit and len(jobs) > limit:
            display_jobs = jobs[:limit]
            print(f"\nShowing top {limit} out of {len(jobs)} jobs:")
        else:
            display_jobs = jobs
            print(f"\nShowing all {len(jobs)} jobs:")
        
        # Format and print header
        header = f"{'ID':<5} | {'Score':<6} | {'Status':<8} | {'Title':<30} | {'Company':<20} | {'Location':<15} | {'Source':<10}"
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        
        # Format and print each job
        for i, job in enumerate(display_jobs):
            print(f"{i+1:<5} | {job.match_score:<6.1f} | {job.status:<8} | {job.title[:30]:<30} | {job.company[:20]:<20} | {job.location[:15]:<15} | {job.job_board:<10}")
        
        print("-" * len(header))
    
    def run_interactive(self):
        """Run in interactive console mode"""
        print("\n====== AI Job Applicant Bot - Console Mode ======\n")
        
        print("What would you like to do?")
        print("1. Search for jobs")
        print("2. Match jobs to resume")
        print("3. Apply to jobs")
        print("4. Display all jobs")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == '1':
            print("\nSearching for jobs...")
            jobs = self.search_jobs()
            print(f"Found {len(jobs)} total jobs")
            self.display_jobs(jobs, limit=10)
            
        elif choice == '2':
            print("\nMatching jobs to resume...")
            all_jobs = self.job_search_manager.get_all_jobs()
            
            if not all_jobs:
                print("No jobs found. Please search for jobs first.")
            else:
                matched_jobs = self.match_jobs(all_jobs)
                self.display_jobs(matched_jobs, limit=10)
            
        elif choice == '3':
            print("\nApplying to jobs...")
            all_jobs = self.job_search_manager.get_all_jobs()
            
            if not all_jobs:
                print("No jobs found. Please search for jobs first.")
            else:
                # Match jobs if not already matched
                if any(job.match_score == 0 for job in all_jobs):
                    print("Some jobs haven't been matched yet. Matching now...")
                    all_jobs = self.match_jobs(all_jobs)
                
                # Sort by match score
                sorted_jobs = sorted(all_jobs, key=lambda j: j.match_score, reverse=True)
                
                # Display top jobs
                self.display_jobs(sorted_jobs, limit=10)
                
                # Get limit from user
                try:
                    limit = int(input("\nHow many jobs do you want to apply to? (1-10): "))
                    limit = max(1, min(10, limit))
                except ValueError:
                    limit = 3
                    print(f"Invalid input. Using default limit of {limit}.")
                
                # Confirm before proceeding
                confirm = input(f"\nAre you sure you want to apply to {limit} jobs? (y/n): ")
                if confirm.lower() == 'y':
                    results = self.apply_to_jobs(sorted_jobs, limit)
                    
                    if results:
                        print("\nApplication Results:")
                        for result in results:
                            status = "Success" if result['success'] else "Failed"
                            print(f"{status}: {result['job_title']} at {result['company']}")
                else:
                    print("Application cancelled.")
            
        elif choice == '4':
            print("\nDisplaying all jobs...")
            all_jobs = self.job_search_manager.get_all_jobs()
            
            if not all_jobs:
                print("No jobs found. Please search for jobs first.")
            else:
                # Ask for sort order
                print("\nSort by:")
                print("1. Match Score (highest first)")
                print("2. Title (A-Z)")
                print("3. Company (A-Z)")
                print("4. Status")
                
                sort_choice = input("\nEnter your choice (1-4): ")
                
                if sort_choice == '1':
                    sorted_jobs = sorted(all_jobs, key=lambda j: j.match_score, reverse=True)
                elif sort_choice == '2':
                    sorted_jobs = sorted(all_jobs, key=lambda j: j.title)
                elif sort_choice == '3':
                    sorted_jobs = sorted(all_jobs, key=lambda j: j.company)
                elif sort_choice == '4':
                    sorted_jobs = sorted(all_jobs, key=lambda j: j.status)
                else:
                    sorted_jobs = all_jobs
                
                # Display all jobs
                self.display_jobs(sorted_jobs)
            
        elif choice == '5':
            print("\nExiting...")
            return False
        
        else:
            print("\nInvalid choice. Please try again.")
        
        # Prompt to continue
        continue_choice = input("\nPress Enter to continue or 'q' to quit: ")
        if continue_choice.lower() == 'q':
            print("\nExiting...")
            return False
        
        return True
    
    def run_automated(self):
        """Run in automated non-interactive mode"""
        print("\n====== AI Job Applicant Bot - Automated Mode ======\n")
        
        # Step 1: Search for jobs
        print("Step 1: Searching for jobs...")
        jobs = self.search_jobs()
        
        if not jobs:
            print("No jobs found. Exiting.")
            return
        
        # Step 2: Match jobs to resume
        print("\nStep 2: Matching jobs to resume...")
        matched_jobs = self.match_jobs(jobs)
        
        # Step 3: Apply to top matching jobs
        print("\nStep 3: Applying to top matching jobs...")
        
        # Get application limit from config
        limit = self.config['application'].get('application_limit_per_day', 3)
        print(f"Application limit per run: {limit}")
        
        # Apply to jobs
        results = self.apply_to_jobs(matched_jobs, limit)
        
        # Print summary
        success_count = sum(1 for r in results if r['success'])
        print(f"\nSuccessfully applied to {success_count} out of {len(results)} jobs")
        
        print("\nAutomated run completed.")


def run_console_mode(config_path: str):
    """
    Run application in console mode
    
    Args:
        config_path: Path to config file
    """
    try:
        # Configure detailed logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/console.log'),
                logging.StreamHandler()
            ]
        )
        
        # Create console application
        app = ConsoleApplication(config_path)
        
        # Check if we should run in interactive or automated mode
        if sys.stdout.isatty():  # Interactive terminal
            # Run interactive loop
            while app.run_interactive():
                pass
        else:  # Non-interactive (e.g., cron job)
            app.run_automated()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"Error in console mode: {e}")
        print(f"\nError: {e}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='AI Job Applicant Bot - Console Mode')
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file')
    args = parser.parse_args()
    
    # Run console mode
    run_console_mode(args.config)
