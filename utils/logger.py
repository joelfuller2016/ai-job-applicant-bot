#!/usr/bin/env python3

"""
Logging Utility

Provides standardized logging functionality for the application.
"""

import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional

def setup_logging(log_dir: str = 'logs', 
                 log_file: Optional[str] = None,
                 log_level: int = logging.INFO,
                 console_level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging with file and console handlers
    
    Args:
        log_dir: Directory to store log files
        log_file: Log file name (optional, generated based on timestamp if None)
        log_level: Logging level for file logging
        console_level: Logging level for console output
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(exist_ok=True)
    
    # Generate log file name if not provided
    if log_file is None:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file = f"app_{timestamp}.log"
    
    log_path = os.path.join(log_dir, log_file)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter
    
    # Remove any existing handlers (to avoid duplicates)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create file handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create a separate CSV log for job applications
    app_log_path = os.path.join(log_dir, 'applications.csv')
    
    # Check if file exists, create with header if not
    if not os.path.exists(app_log_path):
        with open(app_log_path, 'w') as f:
            f.write("timestamp,job_id,title,company,job_board,url,status,notes\n")
    
    return logger


def log_application(log_dir: str = 'logs',
                   timestamp: str = None,
                   job_id: str = '',
                   title: str = '',
                   company: str = '',
                   job_board: str = '',
                   url: str = '',
                   status: str = '',
                   notes: str = ''):
    """
    Log job application to CSV file
    
    Args:
        log_dir: Directory for log files
        timestamp: Timestamp for the log entry (current time if None)
        job_id: Unique job ID
        title: Job title
        company: Company name
        job_board: Source job board
        url: Job URL
        status: Application status
        notes: Additional notes
    """
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(exist_ok=True)
    
    # Generate timestamp if not provided
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Escape any commas in fields
    title = title.replace(',', ' ')
    company = company.replace(',', ' ')
    notes = notes.replace(',', ' ')
    
    # Format CSV line
    csv_line = f"{timestamp},{job_id},{title},{company},{job_board},{url},{status},{notes}\n"
    
    # Append to applications log file
    app_log_path = os.path.join(log_dir, 'applications.csv')
    with open(app_log_path, 'a') as f:
        f.write(csv_line)


# Create a class for tracking job application metrics
class ApplicationMetrics:
    """Tracks job application metrics over time"""
    
    def __init__(self, log_dir: str = 'logs'):
        """
        Initialize metrics tracker
        
        Args:
            log_dir: Directory containing logs
        """
        self.log_dir = log_dir
        self.metrics_file = os.path.join(log_dir, 'metrics.csv')
        
        # Create metrics file with header if it doesn't exist
        if not os.path.exists(self.metrics_file):
            Path(log_dir).mkdir(exist_ok=True)
            with open(self.metrics_file, 'w') as f:
                f.write("date,searches,matches,applications,success_rate\n")
    
    def update_daily_metrics(self):
        """Update metrics based on application logs"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Count searches, matches, and applications
        searches = 0
        matches = 0
        applications = 0
        successes = 0
        
        # Parse application log
        app_log_path = os.path.join(self.log_dir, 'applications.csv')
        if os.path.exists(app_log_path):
            with open(app_log_path, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                
                for line in lines:
                    parts = line.strip().split(',')
                    if len(parts) >= 7:
                        timestamp = parts[0]
                        status = parts[6]
                        
                        # Check if log is from today
                        if timestamp.startswith(today):
                            applications += 1
                            if status == "Applied":
                                successes += 1
        
        # Parse main log for searches and matches
        for log_file in os.listdir(self.log_dir):
            if log_file.endswith('.log'):
                log_path = os.path.join(self.log_dir, log_file)
                with open(log_path, 'r') as f:
                    for line in f:
                        if today in line:
                            if "Searching for jobs" in line:
                                searches += 1
                            elif "Matching jobs to resume" in line:
                                matches += 1
        
        # Calculate success rate
        success_rate = (successes / applications * 100) if applications > 0 else 0
        
        # Write to metrics file
        with open(self.metrics_file, 'a') as f:
            f.write(f"{today},{searches},{matches},{applications},{success_rate:.1f}\n")
        
        return {
            'date': today,
            'searches': searches,
            'matches': matches,
            'applications': applications,
            'success_rate': success_rate
        }
    
    def get_metrics_history(self, days: int = 7):
        """
        Get metrics history for the specified number of days
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of metrics dictionaries, one per day
        """
        history = []
        
        if os.path.exists(self.metrics_file):
            with open(self.metrics_file, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
                
                # Get the last 'days' entries
                for line in lines[-days:]:
                    parts = line.strip().split(',')
                    if len(parts) >= 5:
                        history.append({
                            'date': parts[0],
                            'searches': int(parts[1]),
                            'matches': int(parts[2]),
                            'applications': int(parts[3]),
                            'success_rate': float(parts[4])
                        })
        
        return history


if __name__ == "__main__":
    # Test logging setup
    logger = setup_logging(log_level=logging.DEBUG)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Test application logging
    log_application(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        job_id="test-job-1",
        title="Test Job",
        company="Test Company",
        job_board="Test Board",
        url="https://example.com",
        status="Applied",
        notes="Test application"
    )
    
    # Test metrics
    metrics = ApplicationMetrics()
    daily_metrics = metrics.update_daily_metrics()
    print("Daily Metrics:", daily_metrics)
    
    history = metrics.get_metrics_history(days=7)
    print("Metrics History:", history)
