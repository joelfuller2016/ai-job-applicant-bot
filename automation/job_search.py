#!/usr/bin/env python3

"""
Job Search Module

This module handles searching for jobs across multiple job boards.
"""

import os
import time
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class JobPost:
    """Represents a job posting with all relevant details"""
    
    def __init__(self, 
                 title: str,
                 company: str,
                 location: str,
                 description: str,
                 url: str,
                 job_board: str,
                 date_posted: Optional[str] = None,
                 salary: Optional[str] = None,
                 job_type: Optional[str] = None,
                 apply_url: Optional[str] = None):
        """
        Initialize a job posting
        
        Args:
            title: Job title
            company: Company name
            location: Job location
            description: Full job description
            url: URL of the job posting
            job_board: Source job board (e.g., LinkedIn, Indeed)
            date_posted: Date when the job was posted (optional)
            salary: Salary information (optional)
            job_type: Job type (e.g., Full-time, Contract) (optional)
            apply_url: Direct application URL if different from posting URL (optional)
        """
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.url = url
        self.job_board = job_board
        self.date_posted = date_posted
        self.salary = salary
        self.job_type = job_type
        self.apply_url = apply_url or url
        
        # Additional fields for internal use
        self.id = self._generate_id()
        self.match_score = 0.0
        self.status = "New"
        self.date_applied = None
        self.notes = None
        
    def _generate_id(self) -> str:
        """Generate a unique ID for the job posting"""
        # Use company name and first few words of title to create a semi-unique ID
        company_part = self.company.lower().replace(' ', '-')[:20]
        title_part = self.title.lower().replace(' ', '-')[:30]
        return f"{self.job_board.lower()}-{company_part}-{title_part}"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert job posting to dictionary for serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'description': self.description,
            'url': self.url,
            'job_board': self.job_board,
            'date_posted': self.date_posted,
            'salary': self.salary,
            'job_type': self.job_type,
            'apply_url': self.apply_url,
            'match_score': self.match_score,
            'status': self.status,
            'date_applied': self.date_applied,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobPost':
        """Create a JobPost instance from a dictionary"""
        job = cls(
            title=data['title'],
            company=data['company'],
            location=data['location'],
            description=data['description'],
            url=data['url'],
            job_board=data['job_board'],
            date_posted=data.get('date_posted'),
            salary=data.get('salary'),
            job_type=data.get('job_type'),
            apply_url=data.get('apply_url')
        )
        
        # Set additional fields
        job.id = data['id']
        job.match_score = data.get('match_score', 0.0)
        job.status = data.get('status', 'New')
        job.date_applied = data.get('date_applied')
        job.notes = data.get('notes')
        
        return job


class JobBoardScraper(ABC):
    """Abstract base class for job board scrapers"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scraper with configuration
        
        Args:
            config: Dictionary with job board configuration
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    @abstractmethod
    def search_jobs(self, job_titles: List[str], remote_only: bool = True) -> List[JobPost]:
        """
        Search for jobs with the given titles
        
        Args:
            job_titles: List of job titles to search for
            remote_only: Whether to search for remote jobs only
            
        Returns:
            List of JobPost objects
        """
        pass
    
    @abstractmethod
    def login(self) -> bool:
        """
        Log in to the job board (if required)
        
        Returns:
            bool: True if login successful, False otherwise
        """
        pass
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location string"""
        if not location:
            return "Unknown"
        
        location = location.strip()
        
        # Handle common remote indicators
        remote_indicators = ["remote", "work from home", "wfh", "virtual", "anywhere"]
        for indicator in remote_indicators:
            if indicator in location.lower():
                return "Remote"
        
        return location


class LinkedInScraper(JobBoardScraper):
    """LinkedIn job board scraper"""
    
    def login(self) -> bool:
        """Log in to LinkedIn"""
        if not self.config.get('username') or not self.config.get('password'):
            logger.warning("LinkedIn username or password not provided. Some features may be limited.")
            return False
        
        # Simplified implementation - in production, would use Playwright
        logger.info("LinkedIn authentication would be implemented here with Playwright")
        return True
    
    def search_jobs(self, job_titles: List[str], remote_only: bool = True) -> List[JobPost]:
        """Search for jobs on LinkedIn"""
        results = []
        
        for title in job_titles:
            logger.info(f"Searching LinkedIn for: {title}")
            
            # In a real implementation, this would use Playwright to navigate and scrape
            # This is a simplified placeholder
            
            # Simulate finding some jobs
            for i in range(3):
                job = JobPost(
                    title=f"{title}",
                    company=f"Company {i+1}",
                    location="Remote" if remote_only else f"City {i+1}",
                    description=f"This is a sample job description for {title} at Company {i+1}...",
                    url=f"https://linkedin.com/jobs/view/job{i+1}",
                    job_board="LinkedIn",
                    date_posted=datetime.now().strftime("%Y-%m-%d"),
                    job_type="Full-time"
                )
                results.append(job)
            
            # Simulate delay between searches to avoid rate limiting
            time.sleep(1)
        
        logger.info(f"Found {len(results)} jobs on LinkedIn")
        return results


class IndeedScraper(JobBoardScraper):
    """Indeed job board scraper"""
    
    def login(self) -> bool:
        """Log in to Indeed"""
        if not self.config.get('username') or not self.config.get('password'):
            logger.warning("Indeed username or password not provided. Some features may be limited.")
            return False
        
        # Simplified implementation - in production, would use Playwright
        logger.info("Indeed authentication would be implemented here with Playwright")
        return True
    
    def search_jobs(self, job_titles: List[str], remote_only: bool = True) -> List[JobPost]:
        """Search for jobs on Indeed"""
        results = []
        
        for title in job_titles:
            logger.info(f"Searching Indeed for: {title}")
            
            # In a real implementation, this would use Playwright to navigate and scrape
            # This is a simplified placeholder
            
            # Simulate finding some jobs
            for i in range(3):
                job = JobPost(
                    title=f"{title}",
                    company=f"Company {i+4}",  # Different from LinkedIn
                    location="Remote" if remote_only else f"City {i+4}",
                    description=f"This is a sample job description for {title} at Company {i+4}...",
                    url=f"https://indeed.com/jobs/view/job{i+4}",
                    job_board="Indeed",
                    date_posted=datetime.now().strftime("%Y-%m-%d"),
                    salary=f"${90000 + i*10000} - ${110000 + i*10000}",
                    job_type="Full-time"
                )
                results.append(job)
            
            # Simulate delay between searches to avoid rate limiting
            time.sleep(1)
        
        logger.info(f"Found {len(results)} jobs on Indeed")
        return results


class DiceScraper(JobBoardScraper):
    """Dice job board scraper"""
    
    def login(self) -> bool:
        """Dice doesn't require login for job search"""
        return True
    
    def search_jobs(self, job_titles: List[str], remote_only: bool = True) -> List[JobPost]:
        """Search for jobs on Dice"""
        results = []
        
        for title in job_titles:
            logger.info(f"Searching Dice for: {title}")
            
            # In a real implementation, this would use Playwright to navigate and scrape
            # This is a simplified placeholder
            
            # Simulate finding some jobs
            for i in range(3):
                job = JobPost(
                    title=f"{title}",
                    company=f"Tech Company {i+1}",
                    location="Remote" if remote_only else f"Tech Hub {i+1}",
                    description=f"This is a sample job description for {title} at Tech Company {i+1}...",
                    url=f"https://dice.com/jobs/view/job{i+1}",
                    job_board="Dice",
                    date_posted=datetime.now().strftime("%Y-%m-%d"),
                    job_type="Full-time"
                )
                results.append(job)
            
            # Simulate delay between searches to avoid rate limiting
            time.sleep(1)
        
        logger.info(f"Found {len(results)} jobs on Dice")
        return results


class RemoteOKScraper(JobBoardScraper):
    """RemoteOK job board scraper"""
    
    def login(self) -> bool:
        """RemoteOK doesn't require login for job search"""
        return True
    
    def search_jobs(self, job_titles: List[str], remote_only: bool = True) -> List[JobPost]:
        """Search for jobs on RemoteOK (all jobs are remote)"""
        results = []
        
        for title in job_titles:
            logger.info(f"Searching RemoteOK for: {title}")
            
            # In a real implementation, this would use requests + BeautifulSoup or Playwright
            # This is a simplified placeholder
            
            # Simulate finding some jobs
            for i in range(2):
                job = JobPost(
                    title=f"{title}",
                    company=f"Remote Company {i+1}",
                    location="Remote",  # Always remote on RemoteOK
                    description=f"This is a sample job description for {title} at Remote Company {i+1}...",
                    url=f"https://remoteok.io/jobs/{i+1}",
                    job_board="RemoteOK",
                    date_posted=datetime.now().strftime("%Y-%m-%d"),
                    salary=f"${100000 + i*15000} - ${120000 + i*15000}",
                    job_type="Full-time"
                )
                results.append(job)
            
            # Simulate delay between searches to avoid rate limiting
            time.sleep(1)
        
        logger.info(f"Found {len(results)} jobs on RemoteOK")
        return results


class AngelListScraper(JobBoardScraper):
    """AngelList (now Wellfound) job board scraper"""
    
    def login(self) -> bool:
        """Log in to AngelList"""
        if not self.config.get('username') or not self.config.get('password'):
            logger.warning("AngelList username or password not provided. Some features may be limited.")
            return False
        
        # Simplified implementation - in production, would use Playwright
        logger.info("AngelList authentication would be implemented here with Playwright")
        return True
    
    def search_jobs(self, job_titles: List[str], remote_only: bool = True) -> List[JobPost]:
        """Search for jobs on AngelList"""
        results = []
        
        for title in job_titles:
            logger.info(f"Searching AngelList for: {title}")
            
            # In a real implementation, this would use Playwright to navigate and scrape
            # This is a simplified placeholder
            
            # Simulate finding some jobs
            for i in range(2):
                job = JobPost(
                    title=f"{title} at Startup",
                    company=f"Startup {i+1}",
                    location="Remote" if remote_only else f"Startup Hub {i+1}",
                    description=f"This is a sample job description for {title} at Startup {i+1}...",
                    url=f"https://angel.co/company/startup{i+1}/jobs",
                    job_board="AngelList",
                    date_posted=datetime.now().strftime("%Y-%m-%d"),
                    job_type="Full-time"
                )
                results.append(job)
            
            # Simulate delay between searches to avoid rate limiting
            time.sleep(1)
        
        logger.info(f"Found {len(results)} jobs on AngelList")
        return results


class JobSearchManager:
    """Manages job searching across multiple job boards"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with configuration
        
        Args:
            config: Dictionary with job search configuration
        """
        self.config = config
        self.job_board_scrapers = self._initialize_scrapers()
        self.jobs_db_path = Path('jobs_database.json')
        self.jobs_database = self._load_jobs_database()
        
    def _initialize_scrapers(self) -> Dict[str, JobBoardScraper]:
        """Initialize all job board scrapers"""
        scrapers = {}
        
        # Initialize LinkedIn scraper if enabled
        if self.config['job_boards'].get('linkedin', {}).get('enabled', False):
            scrapers['linkedin'] = LinkedInScraper(self.config['job_boards']['linkedin'])
            
        # Initialize Indeed scraper if enabled
        if self.config['job_boards'].get('indeed', {}).get('enabled', False):
            scrapers['indeed'] = IndeedScraper(self.config['job_boards']['indeed'])
            
        # Initialize Dice scraper if enabled
        if self.config['job_boards'].get('dice', {}).get('enabled', False):
            scrapers['dice'] = DiceScraper(self.config['job_boards']['dice'])
            
        # Initialize RemoteOK scraper if enabled
        if self.config['job_boards'].get('remoteok', {}).get('enabled', False):
            scrapers['remoteok'] = RemoteOKScraper(self.config['job_boards']['remoteok'])
            
        # Initialize AngelList scraper if enabled
        if self.config['job_boards'].get('angellist', {}).get('enabled', False):
            scrapers['angellist'] = AngelListScraper(self.config['job_boards']['angellist'])
        
        return scrapers
    
    def _load_jobs_database(self) -> Dict[str, JobPost]:
        """Load jobs database from file"""
        if not self.jobs_db_path.exists():
            return {}
        
        try:
            with open(self.jobs_db_path, 'r') as f:
                data = json.load(f)
                
            jobs = {}
            for job_dict in data:
                job = JobPost.from_dict(job_dict)
                jobs[job.id] = job
                
            logger.info(f"Loaded {len(jobs)} jobs from database")
            return jobs
        except Exception as e:
            logger.error(f"Error loading jobs database: {e}")
            return {}
    
    def _save_jobs_database(self):
        """Save jobs database to file"""
        try:
            data = [job.to_dict() for job in self.jobs_database.values()]
            with open(self.jobs_db_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(data)} jobs to database")
        except Exception as e:
            logger.error(f"Error saving jobs database: {e}")
    
    def search_all_job_boards(self) -> List[JobPost]:
        """
        Search all enabled job boards for jobs matching the criteria
        
        Returns:
            List of new JobPost objects (not previously in database)
        """
        job_titles = self.config['job_search']['titles']
        remote_only = self.config['job_search'].get('remote_only', True)
        
        all_new_jobs = []
        
        # Search each enabled job board
        for name, scraper in self.job_board_scrapers.items():
            try:
                logger.info(f"Searching {name} for jobs...")
                
                # Log in if needed
                scraper.login()
                
                # Search for jobs
                jobs = scraper.search_jobs(job_titles, remote_only)
                
                # Add new jobs to database
                new_jobs = self._add_jobs_to_database(jobs)
                all_new_jobs.extend(new_jobs)
                
                logger.info(f"Found {len(new_jobs)} new jobs on {name}")
                
            except Exception as e:
                logger.error(f"Error searching {name}: {e}")
        
        # Save updated database
        self._save_jobs_database()
        
        return all_new_jobs
    
    def _add_jobs_to_database(self, jobs: List[JobPost]) -> List[JobPost]:
        """
        Add jobs to database if they don't already exist
        
        Args:
            jobs: List of JobPost objects to add
            
        Returns:
            List of newly added JobPost objects
        """
        new_jobs = []
        
        for job in jobs:
            # Check if job already exists in database
            if job.id not in self.jobs_database:
                # Apply filters to job
                if self._apply_job_filters(job):
                    # Add to database
                    self.jobs_database[job.id] = job
                    new_jobs.append(job)
        
        return new_jobs
    
    def _apply_job_filters(self, job: JobPost) -> bool:
        """
        Apply filters to job to determine if it should be included
        
        Args:
            job: JobPost to filter
            
        Returns:
            bool: True if job passes filters, False otherwise
        """
        # Check for excluded keywords in title
        exclude_keywords = self.config['job_search'].get('exclude_keywords', [])
        for keyword in exclude_keywords:
            if keyword.lower() in job.title.lower():
                logger.debug(f"Job '{job.title}' excluded due to keyword: {keyword}")
                return False
        
        # Check for required location
        if self.config['job_search'].get('remote_only', True):
            if "remote" not in job.location.lower():
                logger.debug(f"Job '{job.title}' excluded as it's not remote")
                return False
        
        # Additional filters can be added here
        
        return True
    
    def get_all_jobs(self) -> List[JobPost]:
        """Get all jobs in the database"""
        return list(self.jobs_database.values())
    
    def get_jobs_by_status(self, status: str) -> List[JobPost]:
        """Get jobs with the specified status"""
        return [job for job in self.jobs_database.values() if job.status == status]
    
    def update_job_status(self, job_id: str, status: str, notes: Optional[str] = None):
        """Update the status of a job"""
        if job_id in self.jobs_database:
            self.jobs_database[job_id].status = status
            
            if status == "Applied":
                self.jobs_database[job_id].date_applied = datetime.now().strftime("%Y-%m-%d")
                
            if notes:
                self.jobs_database[job_id].notes = notes
                
            self._save_jobs_database()
        else:
            logger.warning(f"Job ID {job_id} not found in database")
    
    def update_job_match_score(self, job_id: str, match_score: float):
        """Update the match score of a job"""
        if job_id in self.jobs_database:
            self.jobs_database[job_id].match_score = match_score
            self._save_jobs_database()
        else:
            logger.warning(f"Job ID {job_id} not found in database")


if __name__ == "__main__":
    # Simple test code
    import json
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Sample configuration
    config = {
        "job_search": {
            "titles": [
                "Senior Software Developer",
                "Senior Software Engineer"
            ],
            "remote_only": True,
            "exclude_keywords": ["junior", "internship"]
        },
        "job_boards": {
            "linkedin": {
                "enabled": True,
                "username": "",
                "password": ""
            },
            "indeed": {
                "enabled": True,
                "username": "",
                "password": ""
            },
            "dice": {
                "enabled": True
            },
            "remoteok": {
                "enabled": True
            },
            "angellist": {
                "enabled": False
            }
        }
    }
    
    # Initialize job search manager
    manager = JobSearchManager(config)
    
    # Search all job boards
    new_jobs = manager.search_all_job_boards()
    
    # Print results
    print(f"Found {len(new_jobs)} new jobs")
    for job in new_jobs:
        print(f"{job.title} at {job.company} ({job.location}) - {job.job_board}")
