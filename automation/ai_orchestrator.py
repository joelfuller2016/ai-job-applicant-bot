#!/usr/bin/env python3

"""
AI Orchestrator

This module orchestrates the entire job search and application process using AI.
It coordinates between the browser-use agent, job analyzer, and other components.
"""

import os
import time
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Import local modules
from automation.browseruse_agent import BrowserUseAgent
from automation.job_analyzer import JobAnalyzer
from cover_letters.generator import CoverLetterGenerator
from resume.parser import ResumeParser
from utils.advanced_logging import get_logger, ActivityLogger
from utils.helpers import load_json_file, save_json_file, generate_id, create_directory_if_not_exists

# Set up logger
logger = get_logger("ai_orchestrator")

class AIJobOrchestrator:
    """
    AI Orchestrator for job search and application
    
    This class coordinates the entire job search and application process,
    using AI to analyze jobs, generate cover letters, and apply to positions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI Orchestrator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Component instances
        self.browser_agent = None
        self.job_analyzer = None
        self.cover_letter_generator = None
        self.resume_parser = None
        
        # Job database
        self.data_dir = Path(config.get('data_dir', 'data'))
        self.jobs_db_path = self.data_dir / 'jobs_database.json'
        self.jobs_db = self._load_jobs_database()
        
        # Activity logger
        self.activity_logger = ActivityLogger(logger)
        
        # Session ID
        self.session_id = generate_id("session_")
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Create data directory if it doesn't exist
            create_directory_if_not_exists(str(self.data_dir))
            
            # Initialize browser agent
            self.browser_agent = BrowserUseAgent(self.config)
            await self.browser_agent.initialize()
            
            # Initialize job analyzer
            self.job_analyzer = JobAnalyzer(self.config)
            await self.job_analyzer.initialize()
            
            # Initialize cover letter generator
            self.cover_letter_generator = CoverLetterGenerator(self.config)
            await self.cover_letter_generator.initialize()
            
            # Initialize resume parser
            self.resume_parser = ResumeParser(self.config)
            
            logger.info("AI Orchestrator initialized successfully")
            return self
            
        except Exception as e:
            logger.error(f"Error initializing AI Orchestrator: {e}")
            raise
    
    def _load_jobs_database(self) -> Dict[str, Any]:
        """Load jobs database from disk"""
        if not self.jobs_db_path.exists():
            return {
                "jobs": [],
                "applications": [],
                "statistics": {
                    "total_jobs_found": 0,
                    "total_applications": 0,
                    "successful_applications": 0
                },
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            with open(self.jobs_db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading jobs database: {e}")
            return {
                "jobs": [],
                "applications": [],
                "statistics": {
                    "total_jobs_found": 0,
                    "total_applications": 0,
                    "successful_applications": 0
                },
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_jobs_database(self):
        """Save jobs database to disk"""
        try:
            # Update last updated timestamp
            self.jobs_db["last_updated"] = datetime.now().isoformat()
            
            with open(self.jobs_db_path, 'w') as f:
                json.dump(self.jobs_db, f, indent=2)
            
            logger.info(f"Jobs database saved successfully: {len(self.jobs_db['jobs'])} jobs, {len(self.jobs_db['applications'])} applications")
            
        except Exception as e:
            logger.error(f"Error saving jobs database: {e}")
    
    async def search_jobs(self, job_board: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for jobs on a specific job board
        
        Args:
            job_board: Name of the job board (linkedin, indeed, etc.)
            search_params: Search parameters (keywords, location, etc.)
            
        Returns:
            List of job dictionaries
        """
        try:
            logger.info(f"Searching for jobs on {job_board} with parameters: {search_params}")
            
            # Use browser agent to search for jobs
            result = await self.browser_agent.search_jobs(job_board, search_params)
            
            if not result.get("success", False):
                logger.error(f"Error searching for jobs on {job_board}: {result.get('error', 'Unknown error')}")
                return []
            
            # Extract jobs from result
            new_jobs = result.get("result", [])
            
            if not new_jobs:
                logger.info(f"No jobs found on {job_board}")
                return []
            
            logger.info(f"Found {len(new_jobs)} jobs on {job_board}")
            
            # Add new jobs to database
            for job in new_jobs:
                # Generate a unique ID if not present
                if "id" not in job:
                    job["id"] = generate_id(f"{job_board}_")
                
                # Add metadata
                job["job_board"] = job_board
                job["found_date"] = datetime.now().isoformat()
                job["status"] = "new"
                job["search_params"] = search_params
                
                # Check if job already exists in database
                existing_job = None
                for db_job in self.jobs_db["jobs"]:
                    if db_job.get("url") == job.get("url"):
                        existing_job = db_job
                        break
                
                if existing_job:
                    # Update existing job
                    existing_job.update(job)
                else:
                    # Add new job
                    self.jobs_db["jobs"].append(job)
                    self.jobs_db["statistics"]["total_jobs_found"] += 1
            
            # Save database
            self._save_jobs_database()
            
            # Log activity
            self.activity_logger.log_job_search(
                job_board,
                search_params.get("keywords", ""),
                search_params.get("location", ""),
                len(new_jobs)
            )
            
            return new_jobs
            
        except Exception as e:
            logger.error(f"Error searching for jobs on {job_board}: {e}")
            return []
    
    async def search_all_job_boards(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for jobs across all enabled job boards
        
        Args:
            search_params: Search parameters (keywords, location, etc.)
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        job_boards = self.config.get('job_boards', {})
        
        for job_board, settings in job_boards.items():
            if settings.get('enabled', False):
                try:
                    # Search this job board
                    jobs = await self.search_jobs(job_board, search_params)
                    all_jobs.extend(jobs)
                    
                    # Add delay between job boards to avoid detection
                    if job_board != list(job_boards.keys())[-1]:  # Skip delay after last job board
                        delay = random.randint(5, 15)
                        logger.info(f"Waiting {delay} seconds before searching next job board...")
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"Error searching {job_board}: {e}")
        
        return all_jobs
    
    async def analyze_job(self, job_id: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a job and compute match score
        
        Args:
            job_id: Job ID
            resume_data: Resume data as a dictionary
            
        Returns:
            Job with analysis
        """
        try:
            # Find job in database
            job = None
            for j in self.jobs_db["jobs"]:
                if j.get("id") == job_id:
                    job = j
                    break
            
            if not job:
                logger.error(f"Job with ID {job_id} not found")
                return None
            
            logger.info(f"Analyzing job: {job.get('title')} at {job.get('company')}")
            
            # Check if job has already been analyzed
            if job.get("status") == "analyzed" and "analysis" in job:
                logger.info(f"Job {job_id} has already been analyzed")
                return job
            
            # Extract job description
            job_description = job.get("description", "")
            
            if not job_description:
                logger.warning(f"Job {job_id} has no description, cannot analyze")
                return job
            
            # Analyze job
            analysis = await self.job_analyzer.analyze_job(job_description, resume_data)
            
            # Update job with analysis
            job["analysis"] = analysis
            job["match_score"] = analysis.get("match_score", 0)
            job["status"] = "analyzed"
            
            # Save database
            self._save_jobs_database()
            
            # Log activity
            self.activity_logger.log_job_analysis(
                job_id,
                job.get("title", ""),
                analysis.get("match_score", 0)
            )
            
            return job
            
        except Exception as e:
            logger.error(f"Error analyzing job {job_id}: {e}")
            return None
    
    async def analyze_all_new_jobs(self, resume_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze all new jobs in the database
        
        Args:
            resume_data: Resume data as a dictionary
            
        Returns:
            List of analyzed jobs
        """
        analyzed_jobs = []
        
        # Get all new jobs
        new_jobs = [j for j in self.jobs_db["jobs"] if j.get("status") == "new"]
        
        if not new_jobs:
            logger.info("No new jobs to analyze")
            return []
        
        logger.info(f"Analyzing {len(new_jobs)} new jobs")
        
        for job in new_jobs:
            try:
                # Analyze job
                analyzed_job = await self.analyze_job(job.get("id"), resume_data)
                
                if analyzed_job:
                    analyzed_jobs.append(analyzed_job)
                
                # Add small delay between analyses to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error analyzing job {job.get('id')}: {e}")
        
        logger.info(f"Analyzed {len(analyzed_jobs)} jobs")
        return analyzed_jobs
    
    async def generate_cover_letter(self, job_id: str, resume_data: Dict[str, Any]) -> str:
        """
        Generate a cover letter for a job
        
        Args:
            job_id: Job ID
            resume_data: Resume data as a dictionary
            
        Returns:
            Path to generated cover letter
        """
        try:
            # Find job in database
            job = None
            for j in self.jobs_db["jobs"]:
                if j.get("id") == job_id:
                    job = j
                    break
            
            if not job:
                logger.error(f"Job with ID {job_id} not found")
                return None
            
            logger.info(f"Generating cover letter for job: {job.get('title')} at {job.get('company')}")
            
            # Analyze job if not already analyzed
            if job.get("status") != "analyzed" or "analysis" not in job:
                job = await self.analyze_job(job_id, resume_data)
            
            if not job:
                logger.error(f"Could not analyze job {job_id}")
                return None
            
            # Generate cover letter
            cover_letter_path = await self.cover_letter_generator.generate_cover_letter(job, resume_data)
            
            # Update job with cover letter path
            job["cover_letter_path"] = str(cover_letter_path)
            job["status"] = "cover_letter_generated"
            
            # Save database
            self._save_jobs_database()
            
            # Log activity
            self.activity_logger.log_cover_letter_generation(
                job_id,
                job.get("title", ""),
                str(cover_letter_path)
            )
            
            return cover_letter_path
            
        except Exception as e:
            logger.error(f"Error generating cover letter for job {job_id}: {e}")
            return None
    
    async def apply_to_job(self, job_id: str, resume_path: str) -> Dict[str, Any]:
        """
        Apply to a job
        
        Args:
            job_id: Job ID
            resume_path: Path to resume file
            
        Returns:
            Application result
        """
        try:
            # Find job in database
            job = None
            for j in self.jobs_db["jobs"]:
                if j.get("id") == job_id:
                    job = j
                    break
            
            if not job:
                logger.error(f"Job with ID {job_id} not found")
                return {
                    "success": False,
                    "error": f"Job with ID {job_id} not found"
                }
            
            logger.info(f"Applying to job: {job.get('title')} at {job.get('company')}")
            
            # Check if job already has a cover letter
            cover_letter_path = job.get("cover_letter_path")
            
            if not cover_letter_path:
                # Load resume data to generate cover letter
                resume_data = {}
                if resume_path.endswith('.json'):
                    resume_data = load_json_file(resume_path)
                else:
                    # Parse resume if not in JSON format
                    resume_data = self.resume_parser.parse_resume(resume_path)
                
                # Generate cover letter
                cover_letter_path = await self.generate_cover_letter(job_id, resume_data)
            
            if not cover_letter_path:
                logger.warning(f"Could not generate cover letter for job {job_id}, applying without cover letter")
            
            # Apply to job
            result = await self.browser_agent.apply_to_job(
                job.get("url"),
                resume_path,
                cover_letter_path
            )
            
            # Update job status based on result
            if result.get("success", False):
                job["status"] = "applied"
                job["application_date"] = datetime.now().isoformat()
                job["application_result"] = result
                
                # Add to applications list
                application = {
                    "job_id": job_id,
                    "date": datetime.now().isoformat(),
                    "resume_path": resume_path,
                    "cover_letter_path": cover_letter_path,
                    "result": result,
                    "success": result.get("success", False)
                }
                
                self.jobs_db["applications"].append(application)
                self.jobs_db["statistics"]["total_applications"] += 1
                
                if result.get("success", False):
                    self.jobs_db["statistics"]["successful_applications"] += 1
            else:
                job["status"] = "application_failed"
                job["application_error"] = result.get("error", "Unknown error")
            
            # Save database
            self._save_jobs_database()
            
            # Log activity
            self.activity_logger.log_job_application(
                job_id,
                job.get("title", ""),
                job.get("company", ""),
                result
            )
            
            return result
            
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
            resume_data: Resume data as a dictionary
            
        Returns:
            Result statistics
        """
        try:
            logger.info(f"Starting job search cycle with parameters: {search_params}")
            
            # Search for jobs
            all_jobs = await self.search_all_job_boards(search_params)
            
            if not all_jobs:
                logger.info("No jobs found during search")
                return {
                    "jobs_found": 0,
                    "jobs_analyzed": 0,
                    "matching_jobs": 0,
                    "applications_attempted": 0,
                    "applications_successful": 0
                }
            
            logger.info(f"Found {len(all_jobs)} jobs")
            
            # Analyze all new jobs
            analyzed_jobs = await self.analyze_all_new_jobs(resume_data)
            
            logger.info(f"Analyzed {len(analyzed_jobs)} jobs")
            
            # Filter for matching jobs
            match_threshold = self.config.get('ai', {}).get('match_threshold', 70)
            matching_jobs = []
            
            for job in analyzed_jobs:
                if job.get("match_score", 0) >= match_threshold:
                    matching_jobs.append(job)
            
            logger.info(f"Found {len(matching_jobs)} matching jobs with score >= {match_threshold}")
            
            # Sort matching jobs by score
            matching_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)
            
            # Apply to matching jobs (limited by daily limit)
            daily_limit = self.config.get('application', {}).get('daily_application_limit', 10)
            
            # Check how many applications we've made today
            today = datetime.now().strftime("%Y-%m-%d")
            applications_today = 0
            
            for app in self.jobs_db["applications"]:
                app_date = app.get("date", "").split("T")[0]
                if app_date == today:
                    applications_today += 1
            
            logger.info(f"Applications made today: {applications_today}/{daily_limit}")
            
            # Calculate how many more applications we can make
            applications_left = daily_limit - applications_today
            applications_attempted = 0
            applications_successful = 0
            
            if applications_left <= 0:
                logger.info("Daily application limit reached")
            else:
                # Apply to top matching jobs
                for job in matching_jobs[:applications_left]:
                    try:
                        logger.info(f"Applying to job: {job.get('title')} at {job.get('company')} (Score: {job.get('match_score')})")
                        
                        # Apply to job
                        result = await self.apply_to_job(job.get("id"), resume_path)
                        applications_attempted += 1
                        
                        if result.get("success", False):
                            applications_successful += 1
                        
                        # Add delay between applications
                        cooldown = self.config.get('application', {}).get('application_cooldown_seconds', 3600)
                        if cooldown > 0 and job != matching_jobs[:applications_left][-1]:  # Skip delay after last job
                            logger.info(f"Waiting {cooldown} seconds before next application...")
                            await asyncio.sleep(cooldown)
                            
                    except Exception as e:
                        logger.error(f"Error applying to job {job.get('id')}: {e}")
            
            # Return statistics
            return {
                "jobs_found": len(all_jobs),
                "jobs_analyzed": len(analyzed_jobs),
                "matching_jobs": len(matching_jobs),
                "applications_attempted": applications_attempted,
                "applications_successful": applications_successful
            }
            
        except Exception as e:
            logger.error(f"Error running job search cycle: {e}")
            return {
                "error": str(e),
                "jobs_found": 0,
                "jobs_analyzed": 0,
                "matching_jobs": 0,
                "applications_attempted": 0,
                "applications_successful": 0
            }
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID
        
        Args:
            job_id: Job ID
            
        Returns:
            Job dictionary or None if not found
        """
        for job in self.jobs_db["jobs"]:
            if job.get("id") == job_id:
                return job
        
        return None
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all jobs
        
        Returns:
            List of all jobs
        """
        return self.jobs_db["jobs"]
    
    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get jobs by status
        
        Args:
            status: Job status
            
        Returns:
            List of jobs with the specified status
        """
        return [job for job in self.jobs_db["jobs"] if job.get("status") == status]
    
    def get_all_applications(self) -> List[Dict[str, Any]]:
        """
        Get all applications
        
        Returns:
            List of all applications
        """
        return self.jobs_db["applications"]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get job and application statistics
        
        Returns:
            Dictionary of statistics
        """
        stats = self.jobs_db.get("statistics", {}).copy()
        
        # Add additional statistics
        stats["total_jobs"] = len(self.jobs_db["jobs"])
        stats["new_jobs"] = len(self.get_jobs_by_status("new"))
        stats["analyzed_jobs"] = len(self.get_jobs_by_status("analyzed"))
        stats["applied_jobs"] = len(self.get_jobs_by_status("applied"))
        
        # Add today's statistics
        today = datetime.now().strftime("%Y-%m-%d")
        stats["applications_today"] = 0
        
        for app in self.jobs_db["applications"]:
            app_date = app.get("date", "").split("T")[0]
            if app_date == today:
                stats["applications_today"] += 1
        
        return stats

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
            "application_cooldown_seconds": 3600
        },
        "job_boards": {
            "linkedin": {
                "enabled": True
            }
        }
    }
    
    # Initialize orchestrator
    orchestrator = AIJobOrchestrator(config)
    await orchestrator.initialize()
    
    # Sample search parameters
    search_params = {
        "keywords": "Python Developer",
        "location": "Remote",
        "remote_only": True
    }
    
    # Run job search cycle
    result = await orchestrator.run_job_search_cycle(
        search_params,
        "resume/data/resume.json",
        {"name": "Test User"}  # Sample resume data
    )
    
    print(f"Job search cycle result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
