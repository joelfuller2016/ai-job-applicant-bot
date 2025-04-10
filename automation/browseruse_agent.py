#!/usr/bin/env python3

"""
Browser-use Agent

Integration with browser-use for undetectable browser automation with ML/vision capabilities.
"""

import os
import time
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import tempfile
import random
from dotenv import load_dotenv

# Import browser-use
from browser_use import Agent

# Import utilities
from utils.advanced_logging import get_logger
from utils.helpers import generate_id, create_directory_if_not_exists, get_random_delay

# Load environment variables
load_dotenv()

# Configure logger
logger = get_logger("browseruse_agent")

class BrowserUseAgent:
    """Browser-use agent for undetectable browser automation with ML/vision capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the browser-use agent
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.ai_config = config.get('ai', {})
        self.browser_config = config.get('browser', {})
        
        # Screenshots directory
        self.screenshot_dir = Path(self.browser_config.get('screenshot_dir', 'logs/screenshots'))
        create_directory_if_not_exists(str(self.screenshot_dir))
        
        # browser-use configuration
        self.headless = os.getenv('BROWSERUSE_HEADLESS', 'false').lower() == 'true'
        self.slow_mo = int(os.getenv('BROWSERUSE_SLOW_MO', self.browser_config.get('slow_mo', 50)))
        
        # LLM configuration
        self.llm_model = self.ai_config.get('llm_model', 'gpt-4-turbo')
        
        # Agent instance
        self.agent = None
        
        # Session ID for tracking
        self.session_id = generate_id("browser_")
        
    async def initialize(self):
        """Initialize the browser-use agent"""
        # Import any necessary LLM providers
        try:
            from langchain_openai import ChatOpenAI
            
            # Create LLM
            self.llm = ChatOpenAI(
                model=self.llm_model,
                temperature=self.ai_config.get('temperature', 0.2),
            )
            
            logger.info(f"Initialized LLM: {self.llm_model}")
            return self
            
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            raise
    
    async def create_agent(self, task: str):
        """
        Create a new browser-use agent
        
        Args:
            task: Task description for the agent
            
        Returns:
            Agent instance
        """
        try:
            logger.info(f"Creating browser-use agent for task: {task}")
            
            # Create browser-use agent
            self.agent = Agent(
                llm=self.llm,
                headless=self.headless,
                slow_mo=self.slow_mo,
                task=task
            )
            
            logger.info("Browser-use agent created successfully")
            return self.agent
        except Exception as e:
            logger.error(f"Error creating browser-use agent: {e}")
            raise
    
    async def run_agent(self, task: str) -> Dict[str, Any]:
        """
        Run the browser-use agent with a task
        
        Args:
            task: Task description
            
        Returns:
            Dict with results
        """
        try:
            logger.info(f"Running browser-use agent with task: {task}")
            
            # Create agent if not already created
            if not self.agent:
                await self.create_agent(task)
            
            # Track start time
            start_time = time.time()
            
            # Run the agent
            result = await self.agent.run(task=task)
            
            # Track end time
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"Browser-use agent completed task in {duration:.2f} seconds")
            
            return {
                "success": True,
                "task": task,
                "result": result,
                "duration": duration,
                "session_id": self.session_id
            }
        except Exception as e:
            logger.error(f"Error running browser-use agent: {e}")
            return {
                "success": False,
                "task": task,
                "error": str(e),
                "session_id": self.session_id
            }
    
    async def search_jobs(self, job_board: str, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for jobs on a specific job board
        
        Args:
            job_board: Name of the job board (linkedin, indeed, etc.)
            search_params: Search parameters (keywords, location, etc.)
            
        Returns:
            Dict with search results
        """
        # Extract search parameters
        keywords = search_params.get("keywords", "")
        location = search_params.get("location", "Remote")
        remote_only = search_params.get("remote_only", True)
        
        # Construct the task description
        remote_text = "remote " if remote_only else ""
        task = f"Search for {remote_text}jobs with the title '{keywords}' in '{location}' on {job_board}. " + \
               f"Extract at least 10 job listings with their titles, companies, locations, and URLs. " + \
               f"If there is a job description available, extract that as well. " + \
               f"Return the data in a structured format."
        
        # Add job board-specific instructions
        if job_board.lower() == "linkedin":
            job_board_url = "https://www.linkedin.com/jobs/"
            task += f" Go to {job_board_url} and search for these jobs."
            
        elif job_board.lower() == "indeed":
            job_board_url = "https://www.indeed.com/"
            task += f" Go to {job_board_url} and search for these jobs."
            
        elif job_board.lower() == "dice":
            job_board_url = "https://www.dice.com/"
            task += f" Go to {job_board_url} and search for these jobs."
            
        elif job_board.lower() == "remoteok":
            job_board_url = "https://remoteok.com/"
            search_term = keywords.replace(" ", "-").lower()
            job_board_url = f"https://remoteok.com/remote-{search_term}-jobs"
            task += f" Go to {job_board_url} to view these jobs."
        
        # Run the agent with this task
        result = await self.run_agent(task)
        
        # Add job board info to the result
        result["job_board"] = job_board
        result["search_params"] = search_params
        
        # Take a screenshot if agent was successful
        if result.get("success", False) and self.agent:
            try:
                # Let's capture a screenshot of the results
                timestamp = int(time.time())
                screenshot_path = self.screenshot_dir / f"{job_board}_search_{timestamp}.png"
                
                # To be implemented: capture screenshot using browser-use
                # For now, we'll log a placeholder
                logger.info(f"Would save screenshot to {screenshot_path}")
                
                # Add screenshot path to result
                result["screenshot"] = str(screenshot_path)
            except Exception as e:
                logger.error(f"Error capturing screenshot: {e}")
        
        return result
    
    async def apply_to_job(self, job_url: str, resume_path: str, cover_letter_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply to a job posting
        
        Args:
            job_url: URL of the job posting
            resume_path: Path to resume file
            cover_letter_path: Path to cover letter file (optional)
            
        Returns:
            Dict with application results
        """
        # Verify files exist
        if not os.path.exists(resume_path):
            logger.error(f"Resume file not found: {resume_path}")
            return {
                "success": False,
                "error": f"Resume file not found: {resume_path}",
                "session_id": self.session_id
            }
        
        if cover_letter_path and not os.path.exists(cover_letter_path):
            logger.error(f"Cover letter file not found: {cover_letter_path}")
            return {
                "success": False,
                "error": f"Cover letter file not found: {cover_letter_path}",
                "session_id": self.session_id
            }
        
        # Construct task description
        task = f"Apply to the job at {job_url}. "
        task += f"Use my resume located at {resume_path}. "
        
        if cover_letter_path:
            task += f"Use my cover letter located at {cover_letter_path}. "
        
        task += "Fill out the application form with my information. "
        
        # Add instructions about human approval if required
        if self.config.get("application", {}).get("human_approval_required", True):
            task += "Stop before submitting the application and wait for my approval. "
            task += "Take a screenshot of the filled application form. "
        else:
            # Only submit automatically if explicitly configured to do so
            if self.config.get("application", {}).get("auto_submit", False):
                task += "Submit the application when all required fields are filled. "
            else:
                task += "Stop before submitting the application and wait for my approval. "
        
        # Run the agent with this task
        result = await self.run_agent(task)
        
        # Add application info to the result
        result["job_url"] = job_url
        result["resume_path"] = resume_path
        result["cover_letter_path"] = cover_letter_path
        
        # Take a screenshot if agent was successful
        if result.get("success", False) and self.agent:
            try:
                # Let's capture a screenshot of the application
                timestamp = int(time.time())
                screenshot_path = self.screenshot_dir / f"application_{timestamp}.png"
                
                # To be implemented: capture screenshot using browser-use
                # For now, we'll log a placeholder
                logger.info(f"Would save screenshot to {screenshot_path}")
                
                # Add screenshot path to result
                result["screenshot"] = str(screenshot_path)
            except Exception as e:
                logger.error(f"Error capturing screenshot: {e}")
        
        return result

# Example usage
async def main():
    # Sample configuration
    config = {
        "ai": {
            "llm_model": "gpt-4-turbo",
            "temperature": 0.2
        },
        "browser": {
            "headless": False,
            "slow_mo": 50,
            "screenshot_dir": "logs/screenshots"
        },
        "application": {
            "human_approval_required": True,
            "auto_submit": False
        }
    }
    
    # Create agent
    agent = BrowserUseAgent(config)
    await agent.initialize()
    
    # Search for jobs
    search_params = {
        "keywords": "Software Engineer",
        "location": "Remote",
        "remote_only": True
    }
    
    result = await agent.search_jobs("linkedin", search_params)
    print(f"Search result: {result}")
    
    # Apply to a job
    # job_url = "https://www.example.com/job/123"
    # resume_path = "resume/data/resume.pdf"
    # cover_letter_path = "cover_letters/generated/cover_letter.pdf"
    # result = await agent.apply_to_job(job_url, resume_path, cover_letter_path)
    # print(f"Application result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
