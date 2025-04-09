#!/usr/bin/env python3

"""
AI Job Applicant Bot

An autonomous agent that searches for jobs, matches them to your resume, and applies automatically.
"""

import os
import logging
import argparse
from pathlib import Path

# Create necessary directories if they don't exist
for directory in ['logs', 'resume/data', 'cover_letters/generated', 'config']:
    Path(directory).mkdir(parents=True, exist_ok=True)

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

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='AI Job Applicant Bot')
    parser.add_argument('--no-ui', action='store_true', help='Run without UI (command line only)')
    parser.add_argument('--config', type=str, default='config/config.json', help='Path to config file')
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        logger.info(f"Please copy config/config.example.json to {args.config} and configure it with your details.")
        return
    
    if args.no_ui:
        # Run in console mode
        logger.info("Running in console mode...")
        from automation.console_runner import run_console_mode
        run_console_mode(config_path=args.config)
    else:
        # Launch the Streamlit UI
        logger.info("Launching Streamlit UI...")
        import subprocess
        subprocess.run(['streamlit', 'run', 'ui/app.py', '--', f'--config={args.config}'])

if __name__ == "__main__":
    main()
