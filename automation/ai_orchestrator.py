#!/usr/bin/env python3

"""
AI Job Orchestrator

Main orchestrator for the job search and application process.
Coordinates between browser automation, job analysis, resume parsing, and cover letter generation.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

# Import application components
from automation.browseruse_agent import BrowserUseAgent
from automation.job_analyzer import JobAnalyzer
from cover_letters.generator import CoverLetterGenerator
from resume.ai_parser import AIResumeParser

# Import utilities
from utils.advanced_logging import get_logger, ActivityLogger
from utils.helpers import save_json_file, load_json_file, generate_id, create_directory_if_not_exists

# Configure logger
logger = get_logger("ai_orchestrator")

class AIJobOrchestrator:
    """
    Main orchestrator for the AI job search and application process.
    Manages the entire workflow from job search to application.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Create necessary directories
        self.data_dir = Path(config.get("data_dir", "data"))
        create_directory_if_not_exists(str(self.data_dir))
        
        # Job database path
        self.jobs_db_path = self.data_dir / "jobs_database.json"
        
        # Component instances
        self.browser_agent = None
        self.job_analyzer = None
        self.cover_letter_generator = None
        self.resume_parser = None
        
        # Session tracking
        self.session_id = generate_id("session_")
        
        # Application settings
        self.application_settings = config.get("application", {})
        self.daily_application_limit = self.application_settings.get("daily_application_limit", 10)
        self.match_threshold = config.get("ai", {}).get("match_threshold", 70)
        
        # Activity logger
        self.activity_logger = ActivityLogger(logger, "user")
    
    async def initialize(self):
        """Initialize the orchestrator components"""
        try:
            logger.info("Initializing AI Job Orchestrator...")
            
            # Initialize browser agent
            self.browser_agent = BrowserUseAgent(self.config)
            await self.browser_agent.initialize()
            logger.info("Browser agent initialized")
            
            # Initialize job analyzer
            self.job_analyzer = JobAnalyzer(self.config)
            await self.job_analyzer.initialize()
            logger.info("Job analyzer initialized")
            
            # Initialize cover letter generator
            self.cover_letter_generator = CoverLetterGenerator(self.config)
            await self.cover_letter_generator.initialize()
            logger.info("Cover letter generator initialized")
            
            # Initialize resume parser
            self.resume_parser = AIResumeParser(self.config)
            await self.resume_parser.initialize()
            logger.info("Resume parser initialized")
            
            logger.info("AI Job Orchestrator initialized successfully")
            
            return self
            
        except Exception as e:
            logger.error(f"Error initializing AI Job Orchestrator: {e}")
            raise
    
    async def search_for_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for jobs across multiple job boards
        
        Args:
            search_params: Search parameters
            
        Returns:
            List of job dictionaries
        """
        try:
            logger.info(f"Searching for jobs with parameters: {search_params}")
            
            # Load job database
            jobs_db = self._load_jobs_database()
            
            # Get enabled job boards
            job_boards = self.config.get("job_boards", {})
            enabled_boards = [board for board, settings in job_boards.items() if settings.get("enabled", False)]
            
            if not enabled_boards:
                logger.warning("No job boards enabled in configuration")
                return []
            
            logger.info(f"Searching on enabled job boards: {', '.join(enabled_boards)}")
            
            all_jobs = []
            
            # Search each job board
            for job_board in enabled_boards:
                try:
                    # Log job search
                    self.activity_logger.log_job_search(
                        job_board, 
                        search_params.get("keywords", ""),
                        search_params.get("location", "Remote"),
                        0  # Will update with actual count later
                    )
                    
                    # Search for jobs
                    result = await self.browser_agent.search_jobs(job_board, search_params)
                    
                    if result.get("success", False):
                        # Extract jobs from result
                        jobs = result.get("result", {}).get("jobs", [])
                        
                        if jobs:
                            logger.info(f"Found {len(jobs)} jobs on {job_board}")
                            
                            # Update activity log with actual count
                            self.activity_logger.log_job_search(
                                job_board, 
                                search_params.get("keywords", ""),
                                search_params.get("location", "Remote"),
                                len(jobs)
                            )
                            
                            # Add job board info
                            for job in jobs:
                                job["job_board"] = job_board
                                job["search_date"] = datetime.now().isoformat()
                                job["search_params"] = search_params
                                
                                # Generate ID if not present
                                if "id" not in job:
                                    job["id"] = generate_id(f"{job_board}_")
                                
                                # Set initial status
                                job["status"] = "new"
                                
                                # Add to all jobs
                                all_jobs.append(job)
                        else:
                            logger.info(f"No jobs found on {job_board}")
                    else:
                        logger.error(f"Error searching {job_board}: {result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    logger.error(f"Error searching {job_board}: {e}")
                
                # Add delay between job boards to avoid detection
                if job_board != enabled_boards[-1]:  # Skip delay after last board
                    delay = self.config.get("job_search", {}).get("delay_between_boards", 5)
                    logger.info(f"Waiting {delay} seconds before searching next job board...")
                    await asyncio.sleep(delay)
            
            # Update jobs database with new jobs
            jobs_updated = 0
            
            for job in all_jobs:
                job_id = job.get("id")
                
                # Check if job already exists
                if job_id not in jobs_db["jobs"]:
                    jobs_db["jobs"][job_id] = job
                    jobs_updated += 1
                # If job exists but current status is 'new', update with new job data
                elif jobs_db["jobs"][job_id].get("status") == "new":
                    jobs_db["jobs"][job_id].update(job)
                    jobs_updated += 1
            
            logger.info(f"Added/updated {jobs_updated} jobs in database")
            
            # Save updated database
            self._save_jobs_database(jobs_db)
            
            return all_jobs
            
        except Exception as e:
            logger.error(f"Error searching for jobs: {e}")
            return []
    
    async def analyze_jobs(self, resume_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze jobs in the database
        
        Args:
            resume_data: Resume data
            
        Returns:
            List of analyzed jobs
        """
        try:
            logger.info("Analyzing jobs in the database...")
            
            # Load job database
            jobs_db = self._load_jobs_database()
            
            # Get jobs with status 'new'
            new_jobs = {job_id: job for job_id, job in jobs_db["jobs"].items() if job.get("status") == "new"}
            
            if not new_jobs:
                logger.info("No new jobs to analyze")
                return []
            
            logger.info(f"Found {len(new_jobs)} new jobs to analyze")
            
            analyzed_jobs = []
            
            # Analyze each job
            for job_id, job in new_jobs.items():
                try:
                    # Get job description
                    job_description = job.get("description", "")
                    
                    if not job_description:
                        logger.warning(f"Job {job_id} has no description, skipping analysis")
                        continue
                    
                    # Log job analysis
                    logger.info(f"Analyzing job {job_id}: {job.get('title')} at {job.get('company')}")
                    
                    # Analyze job
                    analysis = await self.job_analyzer.analyze_job(job_description, resume_data)
                    
                    # Get match score
                    match_score = analysis.get("match_score", 0)
                    
                    # Log match score
                    self.activity_logger.log_job_analysis(job_id, job.get("title", ""), match_score)
                    
                    # Update job with analysis
                    job["analysis"] = analysis
                    job["match_score"] = match_score
                    job["status"] = "analyzed"
                    job["analysis_date"] = datetime.now().isoformat()
                    
                    # Add to analyzed jobs
                    analyzed_jobs.append(job)
                    
                    # Update in database
                    jobs_db["jobs"][job_id] = job
                    
                    logger.info(f"Job {job_id} analyzed with match score: {match_score}")
                    
                except Exception as e:
                    logger.error(f"Error analyzing job {job_id}: {e}")
            
            # Save updated database
            self._save_jobs_database(jobs_db)
            
            logger.info(f"Analyzed {len(analyzed_jobs)} jobs")
            
            return analyzed_jobs
            
        except Exception as e:
            logger.error(f"Error analyzing jobs: {e}")
            return []
    
    async def apply_to_job(self, job_id: str, resume_path: str) -> Dict[str, Any]:
        """
        Apply to a specific job
        
        Args:
            job_id: Job ID
            resume_path: Path to resume file
            
        Returns:
            Application result
        """
        try:
            logger.info(f"Applying to job {job_id}...")
            
            # Load job database
            jobs_db = self._load_jobs_database()
            
            # Check if job exists
            if job_id not in jobs_db["jobs"]:
                logger.error(f"Job {job_id} not found in database")
                return {
                    "success": False,
                    "error": f"Job {job_id} not found in database"
                }
            
            # Get job data
            job = jobs_db["jobs"][job_id]
            
            # Check if job already applied
            if job.get("status") == "applied":
                logger.warning(f"Job {job_id} already applied")
                return {
                    "success": False,
                    "error": f"Job {job_id} already applied"
                }
            
            # Generate cover letter
            cover_letter_path = None
            
            try:
                # Generate cover letter
                cover_letter_path = await self.cover_letter_generator.generate_cover_letter(job, resume_path)
                
                # Log cover letter generation
                self.activity_logger.log_cover_letter_generation(job_id, job.get("title", ""), str(cover_letter_path))
                
                logger.info(f"Generated cover letter for job {job_id}: {cover_letter_path}")
                
            except Exception as e:
                logger.error(f"Error generating cover letter for job {job_id}: {e}")
            
            # Apply to job
            job_url = job.get("url", "")
            
            if not job_url:
                logger.error(f"Job {job_id} has no URL")
                return {
                    "success": False,
                    "error": f"Job {job_id} has no URL"
                }
            
            # Apply to job
            result = await self.browser_agent.apply_to_job(job_url, resume_path, cover_letter_path)
            
            # Log application
            self.activity_logger.log_job_application(job_id, job.get("title", ""), job.get("company", ""), result)
            
            # Update job status
            if result.get("success", False):
                job["status"] = "applied"
                job["application_date"] = datetime.now().isoformat()
                job["application_result"] = result
            else:
                job["status"] = "application_failed"
                job["application_error"] = result.get("error", "Unknown error")
            
            # Update in database
            jobs_db["jobs"][job_id] = job
            
            # Add to applications list
            application_id = generate_id("app_")
            jobs_db["applications"][application_id] = {
                "job_id": job_id,
                "application_id": application_id,
                "date": datetime.now().isoformat(),
                "resume_path": str(resume_path),
                "cover_letter_path": str(cover_letter_path) if cover_letter_path else None,
                "result": result
            }
            
            # Save updated database
            self._save_jobs_database(jobs_db)
            
            logger.info(f"Applied to job {job_id} with result: {result.get('success', False)}")
            
            return {
                "success": result.get("success", False),
                "job": job,
                "application_id": application_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error applying to job {job_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_job_search_cycle(self, search_params: Dict[str, Any], resume_path: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete job search and application cycle
        
        Args:
            search_params: Search parameters
            resume_path: Path to resume file
            resume_data: Resume data
            
        Returns:
            Cycle results
        """
        try:
            cycle_start_time = time.time()
            logger.info("Starting job search cycle...")
            
            # Search for jobs
            jobs = await self.search_for_jobs(search_params)
            
            # Analyze jobs
            analyzed_jobs = await self.analyze_jobs(resume_data)
            
            # Filter jobs by match score
            matching_jobs = [job for job in analyzed_jobs if job.get("match_score", 0) >= self.match_threshold]
            
            # Sort by match score (highest first)
            matching_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            
            logger.info(f"Found {len(matching_jobs)} matching jobs above threshold ({self.match_threshold})")
            
            # Check daily application limit
            today = datetime.now().date()
            
            # Load job database
            jobs_db = self._load_jobs_database()
            
            # Count applications today
            applications_today = 0
            
            for app_id, app in jobs_db["applications"].items():
                app_date = datetime.fromisoformat(app.get("date", "2000-01-01")).date()
                if app_date == today:
                    applications_today += 1
            
            logger.info(f"Applications today: {applications_today}/{self.daily_application_limit}")
            
            # Calculate remaining applications
            remaining_applications = max(0, self.daily_application_limit - applications_today)
            
            # Apply to matching jobs
            applied_jobs = []
            
            for job in matching_jobs[:remaining_applications]:
                try:
                    # Apply to job
                    result = await self.apply_to_job(job["id"], resume_path)
                    
                    if result.get("success", False):
                        applied_jobs.append(result)
                    
                    # Add delay between applications
                    if len(applied_jobs) < remaining_applications and len(applied_jobs) < len(matching_jobs):
                        delay = self.application_settings.get("application_cooldown_seconds", 3600)
                        logger.info(f"Waiting {delay} seconds before next application...")
                        await asyncio.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error applying to job {job.get('id')}: {e}")
            
            # Calculate cycle duration
            cycle_end_time = time.time()
            cycle_duration = cycle_end_time - cycle_start_time
            
            logger.info(f"Job search cycle completed in {cycle_duration:.2f} seconds")
            logger.info(f"Jobs found: {len(jobs)}, analyzed: {len(analyzed_jobs)}, matched: {len(matching_jobs)}, applied: {len(applied_jobs)}")
            
            return {
                "success": True,
                "jobs_found": len(jobs),
                "jobs_analyzed": len(analyzed_jobs),
                "matching_jobs": len(matching_jobs),
                "jobs_applied": len(applied_jobs),
                "duration": cycle_duration,
                "date": datetime.now().isoformat(),
                "search_params": search_params
            }
            
        except Exception as e:
            logger.error(f"Error running job search cycle: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _load_jobs_database(self) -> Dict[str, Any]:
        """Load jobs database from disk"""
        if self.jobs_db_path.exists():
            try:
                with open(self.jobs_db_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading jobs database: {e}")
        
        # Return empty database if file doesn't exist or error occurred
        return {
            "jobs": {},
            "applications": {}
        }
    
    def _save_jobs_database(self, jobs_db: Dict[str, Any]) -> bool:
        """Save jobs database to disk"""
        try:
            with open(self.jobs_db_path, 'w') as f:
                json.dump(jobs_db, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving jobs database: {e}")
            return False
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from the database"""
        jobs_db = self._load_jobs_database()
        return list(jobs_db["jobs"].values())
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific job by ID"""
        jobs_db = self._load_jobs_database()
        return jobs_db["jobs"].get(job_id)
    
    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get jobs with a specific status"""
        jobs_db = self._load_jobs_database()
        return [job for job in jobs_db["jobs"].values() if job.get("status") == status]
    
    def get_all_applications(self) -> List[Dict[str, Any]]:
        """Get all applications from the database"""
        jobs_db = self._load_jobs_database()
        return list(jobs_db["applications"].values())
    
    def get_application_by_id(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific application by ID"""
        jobs_db = self._load_jobs_database()
        return jobs_db["applications"].get(application_id)
    
    def get_applications_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a specific job"""
        jobs_db = self._load_jobs_database()
        return [app for app in jobs_db["applications"].values() if app.get("job_id") == job_id]
    
    def update_job_status(self, job_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update the status of a job"""
        jobs_db = self._load_jobs_database()
        
        if job_id in jobs_db["jobs"]:
            jobs_db["jobs"][job_id]["status"] = status
            
            if notes:
                jobs_db["jobs"][job_id]["notes"] = notes
            
            self._save_jobs_database(jobs_db)
            return True
        
        return False
    
    async def parse_resume(self, resume_file_path: str) -> Dict[str, Any]:
        """
        Parse a resume file into structured data
        
        Args:
            resume_file_path: Path to resume file
            
        Returns:
            Parsed resume data
        """
        if not self.resume_parser:
            logger.error("Resume parser not initialized")
            return {}
        
        try:
            return await self.resume_parser.parse_resume(resume_file_path)
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            return {}

# Example usage
async def main():
    # Sample configuration
    config = {
        "ai": {
            "llm_model": "gpt-4-turbo",
            "temperature": 0.2,
            "match_threshold": 70
        },
        "browser": {
            "headless": False,
            "slow_mo": 50,
            "screenshot_dir": "logs/screenshots"
        },
        "application": {
            "daily_application_limit": 10,
            "application_cooldown_seconds": 3600,
            "human_approval_required": True,
            "auto_submit": False
        },
        "job_boards": {
            "linkedin": {
                "enabled": True
            },
            "indeed": {
                "enabled": True
            }
        },
        "data_dir": "data"
    }
    
    # Initialize orchestrator
    orchestrator = AIJobOrchestrator(config)
    await orchestrator.initialize()
    
    # Run a job search cycle
    search_params = {
        "keywords": "Software Engineer",
        "location": "Remote",
        "remote_only": True
    }
    
    resume_path = "resume/data/resume.json"
    
    # Load resume data
    with open(resume_path, 'r') as f:
        resume_data = json.load(f)
    
    result = await orchestrator.run_job_search_cycle(search_params, resume_path, resume_data)
    print(f"Job search cycle result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
