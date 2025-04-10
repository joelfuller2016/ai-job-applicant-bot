#!/usr/bin/env python3

"""
AI Job Applicant Bot

An autonomous agent that searches for jobs, matches them to your resume, and applies automatically.
Uses browser-use for undetectable browser automation with ML/vision capabilities.
"""

import os
import logging
import argparse
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create necessary directories if they don't exist
directories = [
    'logs', 
    'logs/screenshots',
    'resume/data', 
    'cover_letters/generated', 
    'config',
    'data',
    'data/browser_profiles'
]

for directory in directories:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Configure logging
from utils.advanced_logging import setup_logging
logger = setup_logging(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    log_file='logs/app.log'
)

async def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='AI Job Applicant Bot')
    parser.add_argument('--no-ui', action='store_true', help='Run without UI (command line only)')
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file')
    parser.add_argument('--resume', type=str, default='resume/data/resume.json', help='Path to resume JSON file')
    parser.add_argument('--skip-tests', action='store_true', help='Skip startup tests')
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        logger.info(f"Please copy config/config.example.json to {args.config} and configure it with your details.")
        return
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Check for required API keys
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
        return
    
    # Run startup tests
    if not args.skip_tests:
        logger.info("Running startup tests...")
        try:
            from utils.startup_tests import run_all_tests
            test_result = await run_all_tests(args.config)
            
            # Get test summary
            summary = test_result.get_summary()
            logger.info(f"Startup Tests Complete - Passed: {summary['passed']}/{summary['total_tests']} ({summary['success_rate']}%)")
            
            # Check for critical test failures
            failed_tests = test_result.get_failed_tests()
            if failed_tests:
                logger.warning(f"Some startup tests failed ({len(failed_tests)} failures)")
                for test in failed_tests:
                    logger.warning(f"Failed test: {test['name']} - {test['message']}")
                
                # Let the user know they can skip tests
                logger.info("You can skip startup tests with the --skip-tests flag")
        except Exception as e:
            logger.error(f"Error running startup tests: {e}")
            logger.info("Continuing despite test errors...")
    
    if args.no_ui:
        # Run in console mode
        logger.info("Running in console mode...")
        try:
            from automation.ai_orchestrator import AIJobOrchestrator
            
            # Initialize the orchestrator
            orchestrator = await AIJobOrchestrator(config).initialize()
            
            # Load resume data
            if not os.path.exists(args.resume):
                logger.error(f"Resume file not found: {args.resume}")
                logger.info(f"Please create a resume file at {args.resume}")
                return
                
            with open(args.resume, 'r') as f:
                resume_data = json.load(f)
            
            # Run a job search cycle
            search_params = config.get("job_search", {})
            result = await orchestrator.run_job_search_cycle(
                search_params,
                args.resume,
                resume_data
            )
            
            logger.info(f"Job search cycle completed: {result}")
        except Exception as e:
            logger.error(f"Error in console mode: {e}")
    else:
        # Launch the Streamlit UI
        logger.info("Launching Streamlit UI...")
        import subprocess
        subprocess.run([
            'streamlit', 'run', 'ui/app.py', 
            '--', 
            f'--config={args.config}',
            f'--resume={args.resume}',
            '--skip-tests' if args.skip_tests else ''
        ])

if __name__ == "__main__":
    try:
        # Check if we're running in an event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, create a new one
            asyncio.run(main())
        else:
            # Otherwise, use the existing loop
            loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
