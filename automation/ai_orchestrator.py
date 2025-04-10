#!/usr/bin/env python3

"""
AI Job Orchestrator

Coordinates the entire job search and application process using AI components.
Serves as the main controller for the application workflow.
"""

import os
import json
import logging
import asyncio
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

# Import components
from automation.browseruse_agent import BrowserUseAgent
from automation.job_analyzer import JobAnalyzer
from cover_letters.generator import CoverLetterGenerator
from resume.parser import ResumeParser

# Import utilities
from utils.advanced_logging import get_logger, ActivityLogger
from utils.helpers import generate_id, save_json_file, load_json_file, create_directory_if_not_exists

# Load environment variables
load_dotenv()

# Configure logger
logger = get_logger("ai_orchestrator")

class AIJobOrchestrator:
    """
    AI Job Orchestrator
    
    Coordinates the entire job search and application process using AI components.
    Serves as the main controller for the application workflow.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI Job Orchestrator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize session ID
        self.session_id = generate_id("session_")
        
        # Configure activity logger
        self.activity_logger = ActivityLogger(logger, user_id=self.session_id)
        
        # Data directory
        self.data_dir = Path(config.get('data_dir', 'data'))
        create_directory_if_not_exists(str(self.data_dir))
        
        # Database file
        self.jobs_db_path = self.data_dir / "jobs_database.json"
        self.jobs_db = self._load_jobs_database()
        
        # Components
        self.browser_agent = None
        self.job_analyzer = None
        self.cover_letter_generator = None
        self.resume_parser = None
    
    async def initialize(self):
        """Initialize all components"""
        try:
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
            
            logger.info("All components initialized successfully")
            return self
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def _load_jobs_database(self) -> Dict[str, Any]:
        """Load jobs database from disk"""
        if not self.jobs_db_path.exists():
            # Initialize empty database
            jobs_db = {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "version": "2.0.0"
                },
                "jobs": [],
                "applications": []
            }
            # Save initial database
            save_json_file(jobs_db, str(self.jobs_db_path))
            return jobs_db
        
        try:
            return load_json_file(str(self.jobs_db_path))
        except Exception as e:
            logger.error(f"Error loading jobs database: {e}")
            # Return empty database on error
            return {
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "version": "2.0.0"
                },
                "jobs": [],
                "applications": []
            }
    
    def _save_jobs_database(self):
        """Save jobs database to disk"""
        try:
            # Update metadata
            self.jobs_db["metadata"]["updated_at"] = datetime.now().isoformat()
            
            # Save to disk
            save_json_file(self.jobs_db, str(self.jobs_db_path))
            logger.info(f"Jobs database saved with {len(self.jobs_db['jobs'])} jobs and {len(self.jobs_db['applications'])} applications")
        except Exception as e:
            logger.error(f"Error saving jobs database: {e}")
    
    async def search_for_jobs(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for jobs across multiple job boards
        
        Args:
            search_params: Search parameters
            
        Returns:
            List of job dictionaries
        """
        if not self.browser_agent:
            logger.error("Browser agent not initialized")
            return []
        
        all_jobs = []
        job_boards = self.config.get('job_boards', {})
        
        # Track timing
        start_time = time.time()
        
        # Log search start
        logger.info(f"Starting job search with parameters: {search_params}")
        
        # Active job boards (enabled ones)
        active_job_boards = [board for board, settings in job_boards.items() 
                            if settings.get('enabled', False)]
        
        # Randomize order to appear more human-like
        random.shuffle(active_job_boards)
        
        for job_board in active_job_boards:
            try:
                board_settings = job_boards[job_board]
                logger.info(f"Searching for jobs on {job_board}")
                
                # Search job board
                search_result = await self.browser_agent.search_jobs(job_board, search_params)
                
                if not search_result.get('success', False):
                    logger.error(f"Error searching {job_board}: {search_result.get('error', 'Unknown error')}")
                    continue
                
                # Extract jobs from result
                jobs_data = search_result.get('result', {})
                
                # Process jobs
                if isinstance(jobs_data, dict) and 'jobs' in jobs_data:
                    jobs = jobs_data['jobs']
                elif isinstance(jobs_data, list):
                    jobs = jobs_data
                else:
                    jobs = []
                
                # Add job board info to each job
                for job in jobs:
                    if isinstance(job, dict):
                        job['job_board'] = job_board
                        job['found_date'] = datetime.now().isoformat()
                        job['status'] = 'new'
                        
                        # Generate ID if not present
                        if 'id' not in job:
                            job_url = job.get('url', '')
                            job_title = job.get('title', '')
                            job_company = job.get('company', '')
                            job['id'] = generate_id(f"{job_board}_")
                
                # Add to all jobs
                all_jobs.extend(jobs)
                
                # Log jobs found
                self.activity_logger.log_job_search(
                    job_board,
                    search_params.get('keywords', ''),
                    search_params.get('location', ''),
                    len(jobs)
                )
                
                # Add random delay between job boards (1-3 minutes)
                if job_board != active_job_boards[-1]:  # Skip delay after last job board
                    delay = random.randint(60, 180)
                    logger.info(f"Waiting {delay} seconds before searching next job board")
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error searching {job_board}: {e}")
                self.activity_logger.log_error(e, {"job_board": job_board, "action": "search"})
        
        # Process results
        new_jobs_count = 0
        for job in all_jobs:
            # Check if job already exists in database
            if not any(existing_job.get('id') == job.get('id') for existing_job in self.jobs_db['jobs']):
                # Add to database
                self.jobs_db['jobs'].append(job)
                new_jobs_count += 1
        
        # Save database
        self._save_jobs_database()
        
        # Log completion
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Job search completed in {duration:.2f} seconds. Found {len(all_jobs)} jobs ({new_jobs_count} new).")
        
        return all_jobs
    
    async def analyze_jobs(self, resume_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze jobs and determine match with resume
        
        Args:
            resume_data: Resume data dictionary
            
        Returns:
            List of analyzed job dictionaries
        """
        if not self.job_analyzer:
            logger.error("Job analyzer not initialized")
            return []
        
        # Get new jobs (status = 'new')
        new_jobs = [job for job in self.jobs_db['jobs'] if job.get('status') == 'new']
        
        if not new_jobs:
            logger.info("No new jobs to analyze")
            return []
        
        logger.info(f"Analyzing {len(new_jobs)} new jobs")
        
        analyzed_jobs = []
        
        for job in new_jobs:
            try:
                job_id = job.get('id')
                job_title = job.get('title', 'Unknown Title')
                job_company = job.get('company', 'Unknown Company')
                
                logger.info(f"Analyzing job: {job_title} at {job_company}")
                
                # Extract job description
                job_description = job.get('description', '')
                
                if not job_description:
                    logger.warning(f"No description available for job {job_id}")
                    job['status'] = 'incomplete'
                    continue
                
                # Analyze job
                analysis = await self.job_analyzer.analyze_job(job_description, resume_data)
                
                # Add analysis to job
                job['analysis'] = analysis
                job['match_score'] = analysis.get('match_score', 0)
                job['status'] = 'analyzed'
                job['analyzed_date'] = datetime.now().isoformat()
                
                # Log analysis
                self.activity_logger.log_job_analysis(
                    job_id,
                    job_title,
                    analysis.get('match_score', 0)
                )
                
                analyzed_jobs.append(job)
                
                # Add random delay between analyses (5-15 seconds)
                if job != new_jobs[-1]:  # Skip delay after last job
                    delay = random.randint(5, 15)
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error analyzing job {job.get('id')}: {e}")
                self.activity_logger.log_error(e, {"job_id": job.get('id'), "action": "analyze"})
                job['status'] = 'error'
        
        # Save database
        self._save_jobs_database()
        
        logger.info(f"Job analysis completed. Analyzed {len(analyzed_jobs)} jobs.")
        
        return analyzed_jobs
    
    async def generate_cover_letter(self, job_id: str, resume_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a cover letter for a job
        
        Args:
            job_id: Job ID
            resume_data: Resume data dictionary
            
        Returns:
            Path to generated cover letter file, or None on error
        """
        if not self.cover_letter_generator:
            logger.error("Cover letter generator not initialized")
            return None
        
        # Find job in database
        job = next((j for j in self.jobs_db['jobs'] if j.get('id') == job_id), None)
        
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return None
        
        try:
            job_title = job.get('title', 'Unknown Title')
            job_company = job.get('company', 'Unknown Company')
            
            logger.info(f"Generating cover letter for job: {job_title} at {job_company}")
            
            # Generate cover letter
            cover_letter_path = await self.cover_letter_generator.generate_cover_letter(job, resume_data)
            
            if not cover_letter_path:
                logger.error(f"Error generating cover letter for job {job_id}")
                return None
            
            # Log generation
            self.activity_logger.log_cover_letter_generation(
                job_id,
                job_title,
                str(cover_letter_path)
            )
            
            return str(cover_letter_path)
            
        except Exception as e:
            logger.error(f"Error generating cover letter for job {job_id}: {e}")
            self.activity_logger.log_error(e, {"job_id": job_id, "action": "generate_cover_letter"})
            return None
    
    async def apply_to_job(self, job_id: str, resume_path: str, cover_letter_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply to a job
        
        Args:
            job_id: Job ID
            resume_path: Path to resume file
            cover_letter_path: Path to cover letter file (optional)
            
        Returns:
            Application result dictionary
        """
        if not self.browser_agent:
            logger.error("Browser agent not initialized")
            return {"success": False, "error": "Browser agent not initialized"}
        
        # Find job in database
        job = next((j for j in self.jobs_db['jobs'] if j.get('id') == job_id), None)
        
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return {"success": False, "error": f"Job {job_id} not found in database"}
        
        job_title = job.get('title', 'Unknown Title')
        job_company = job.get('company', 'Unknown Company')
        job_url = job.get('url', '')
        
        if not job_url:
            logger.error(f"No URL available for job {job_id}")
            return {"success": False, "error": "No URL available for job"}
        
        logger.info(f"Applying to job: {job_title} at {job_company}")
        
        # Apply to job
        result = await self.browser_agent.apply_to_job(job_url, resume_path, cover_letter_path)
        
        # Record application
        application = {
            "job_id": job_id,
            "date": datetime.now().isoformat(),
            "resume_path": resume_path,
            "cover_letter_path": cover_letter_path,
            "result": result
        }
        
        # Add to database
        self.jobs_db['applications'].append(application)
        
        # Update job status
        job['status'] = 'applied'
        job['application_date'] = datetime.now().isoformat()
        
        # Save database
        self._save_jobs_database()
        
        # Log application
        self.activity_logger.log_job_application(
            job_id,
            job_title,
            job_company,
            result
        )
        
        return result
    
    async def run_job_search_cycle(self, search_params: Dict[str, Any], resume_path: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete job search and application cycle
        
        Args:
            search_params: Search parameters
            resume_path: Path to resume file
            resume_data: Resume data dictionary
            
        Returns:
            Results dictionary
        """
        cycle_id = generate_id("cycle_")
        start_time = time.time()
        
        logger.info(f"Starting job search cycle {cycle_id}")
        
        try:
            # Search for jobs
            jobs = await self.search_for_jobs(search_params)
            
            # Analyze jobs
            analyzed_jobs = await self.analyze_jobs(resume_data)
            
            # Get matching jobs (above threshold)
            match_threshold = self.config.get('ai', {}).get('match_threshold', 70)
            matching_jobs = [job for job in analyzed_jobs if job.get('match_score', 0) >= match_threshold]
            
            # Sort by match score (highest first)
            matching_jobs.sort(key=lambda j: j.get('match_score', 0), reverse=True)
            
            logger.info(f"Found {len(matching_jobs)} matching jobs above threshold ({match_threshold})")
            
            # Apply to jobs
            application_limit = self.config.get('application', {}).get('daily_application_limit', 10)
            applications_made = 0
            application_results = []
            
            # Check today's application count
            today = datetime.now().strftime("%Y-%m-%d")
            today_applications = [
                app for app in self.jobs_db['applications']
                if app.get('date', '').startswith(today)
            ]
            
            if len(today_applications) >= application_limit:
                logger.info(f"Daily application limit reached ({len(today_applications)}/{application_limit})")
            else:
                remaining_limit = application_limit - len(today_applications)
                
                for job in matching_jobs[:remaining_limit]:
                    try:
                        job_id = job.get('id')
                        
                        # Generate cover letter
                        cover_letter_path = await self.generate_cover_letter(job_id, resume_data)
                        
                        # Apply to job
                        result = await self.apply_to_job(job_id, resume_path, cover_letter_path)
                        
                        application_results.append({
                            "job_id": job_id,
                            "result": result
                        })
                        
                        applications_made += 1
                        
                        # Add random delay between applications (60-180 seconds, 1-3 minutes)
                        if job != matching_jobs[:remaining_limit][-1]:  # Skip delay after last job
                            delay = random.randint(60, 180)
                            logger.info(f"Waiting {delay} seconds before next application")
                            await asyncio.sleep(delay)
                        
                    except Exception as e:
                        logger.error(f"Error applying to job {job.get('id')}: {e}")
                        self.activity_logger.log_error(e, {"job_id": job.get('id'), "action": "apply"})
            
            # Compile results
            end_time = time.time()
            duration = end_time - start_time
            
            results = {
                "cycle_id": cycle_id,
                "jobs_found": len(jobs),
                "jobs_analyzed": len(analyzed_jobs),
                "matching_jobs": len(matching_jobs),
                "applications_made": applications_made,
                "application_results": application_results,
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Job search cycle {cycle_id} completed in {duration:.2f} seconds")
            logger.info(f"Results: {len(jobs)} jobs found, {len(analyzed_jobs)} analyzed, {len(matching_jobs)} matching, {applications_made} applications made")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in job search cycle {cycle_id}: {e}")
            self.activity_logger.log_error(e, {"cycle_id": cycle_id, "action": "run_job_search_cycle"})
            
            # Return error results
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                "cycle_id": cycle_id,
                "error": str(e),
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from database"""
        return self.jobs_db.get('jobs', [])
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        return next((job for job in self.jobs_db.get('jobs', []) if job.get('id') == job_id), None)
    
    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get jobs by status"""
        return [job for job in self.jobs_db.get('jobs', []) if job.get('status') == status]
    
    def get_all_applications(self) -> List[Dict[str, Any]]:
        """Get all applications from database"""
        return self.jobs_db.get('applications', [])
    
    def get_applications_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """Get applications for a specific job"""
        return [app for app in self.jobs_db.get('applications', []) if app.get('job_id') == job_id]
    
    def get_today_applications(self) -> List[Dict[str, Any]]:
        """Get applications made today"""
        today = datetime.now().strftime("%Y-%m-%d")
        return [app for app in self.jobs_db.get('applications', []) if app.get('date', '').startswith(today)]

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
        "job_boards": {
            "linkedin": {
                "enabled": True,
                "url": "https://www.linkedin.com/jobs/"
            },
            "indeed": {
                "enabled": True,
                "url": "https://www.indeed.com/"
            }
        },
        "application": {
            "daily_application_limit": 5,
            "human_approval_required": True,
            "auto_submit": False
        },
        "data_dir": "data"
    }
    
    # Initialize orchestrator
    orchestrator = AIJobOrchestrator(config)
    await orchestrator.initialize()
    
    # Sample resume data
    resume_data = {
        "basic_info": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "123-456-7890"
        },
        "skills": [
            "Python",
            "JavaScript",
            "AWS",
            "Docker",
            "Git",
            "REST APIs",
            "SQL"
        ],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Company",
                "start_date": "2018-01",
                "end_date": "2022-12",
                "description": "Developed backend services using Python and AWS.",
                "achievements": [
                    "Reduced API response time by 30%",
                    "Implemented CI/CD pipeline"
                ]
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "institution": "University",
                "date": "2017"
            }
        ]
    }
    
    # Sample search parameters
    search_params = {
        "keywords": "Software Engineer",
        "location": "Remote",
        "remote_only": True
    }
    
    # Run job search cycle
    results = await orchestrator.run_job_search_cycle(
        search_params,
        "resume/data/resume.pdf",
        resume_data
    )
    
    print(f"Job search cycle results: {results}")

if __name__ == "__main__":
    asyncio.run(main())
