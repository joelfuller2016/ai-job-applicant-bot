#!/usr/bin/env python3

"""
Advanced Logging Module

Provides comprehensive logging capabilities for the AI Job Applicant Bot.
Features include:
- Multiple log destinations (console, file)
- Different log levels for different outputs
- JSON-formatted logging for machine parsing
- Log rotation
- Session tracking
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import uuid
import inspect
import platform

# Configure log formatters
CONSOLE_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
FILE_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'
JSON_FORMAT = {
    'timestamp': '%(asctime)s',
    'level': '%(levelname)s',
    'logger': '%(name)s',
    'message': '%(message)s',
    'file': '%(filename)s',
    'line': '%(lineno)d',
    'function': '%(funcName)s',
    'session_id': None,  # Will be populated by JsonFormatter
    'app_version': '2.0.0',
    'platform': platform.system(),
    'python_version': platform.python_version()
}

class JsonFormatter(logging.Formatter):
    """Formats log records as JSON strings"""
    
    def __init__(self, session_id=None):
        super().__init__()
        self.session_id = session_id or str(uuid.uuid4())
        
    def format(self, record):
        log_data = JSON_FORMAT.copy()
        log_data['timestamp'] = self.formatTime(record)
        log_data['level'] = record.levelname
        log_data['logger'] = record.name
        log_data['message'] = record.getMessage()
        log_data['file'] = record.filename
        log_data['line'] = record.lineno
        log_data['function'] = record.funcName
        log_data['session_id'] = self.session_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ['timestamp', 'level', 'logger', 'message', 'file', 'line', 'function',
                         'session_id', 'app_version', 'platform', 'python_version', 'exc_info',
                         'exc_text', 'levelname', 'name', 'filename', 'lineno', 'funcName', 'created',
                         'msecs', 'relativeCreated', 'levelno', 'msg', 'args', 'pathname'] and not key.startswith('_'):
                log_data[key] = value
        
        return json.dumps(log_data)

class SessionLogger:
    """Logger that maintains session context"""
    
    def __init__(self, logger, session_id=None):
        self.logger = logger
        self.session_id = session_id or str(uuid.uuid4())
        
    def _log(self, level, msg, *args, **kwargs):
        """Log with session ID and caller information"""
        # Get caller frame info
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name
        
        # Add extra fields
        extra = kwargs.get('extra', {})
        extra.update({
            'session_id': self.session_id,
            'file': os.path.basename(filename),
            'line': lineno,
            'function': func_name
        })
        kwargs['extra'] = extra
        
        # Call the actual logger
        getattr(self.logger, level)(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        self._log('debug', msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self._log('info', msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._log('warning', msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._log('error', msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self._log('critical', msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        kwargs['exc_info'] = kwargs.get('exc_info', True)
        self._log('error', msg, *args, **kwargs)
    
    def log_event(self, event_type: str, description: str, details: Optional[Dict[str, Any]] = None):
        """Log a structured event"""
        event_data = {
            'event_type': event_type,
            'description': description,
            'details': details or {}
        }
        self.info(f"EVENT: {event_type} - {description}", extra={'event': event_data})

def setup_logging(
    log_level: str = 'INFO',
    log_file: str = 'logs/app.log',
    json_log_file: Optional[str] = 'logs/app.json',
    session_id: Optional[str] = None,
    rotation: str = 'daily',
    max_log_files: int = 30
) -> SessionLogger:
    """
    Set up logging for the application
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        json_log_file: Path to JSON log file (None to disable)
        session_id: Session ID (generated if None)
        rotation: Log rotation policy ('none', 'daily', 'size')
        max_log_files: Maximum number of log files to keep
        
    Returns:
        SessionLogger: Logger with session context
    """
    # Create session ID if not provided
    session_id = session_id or str(uuid.uuid4())
    
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Convert log level string to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Reset root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(numeric_level)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    root_logger.addHandler(console_handler)
    
    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
    root_logger.addHandler(file_handler)
    
    # Add JSON file handler if enabled
    if json_log_file:
        json_handler = logging.FileHandler(json_log_file)
        json_handler.setLevel(numeric_level)
        json_handler.setFormatter(JsonFormatter(session_id=session_id))
        root_logger.addHandler(json_handler)
    
    # Log session start
    app_logger = logging.getLogger('app')
    app_logger.info(f"Logging initialized with session ID: {session_id}")
    
    # Create session logger
    session_logger = SessionLogger(app_logger, session_id)
    session_logger.log_event(
        "session_start",
        "Application session started",
        {
            "log_level": log_level,
            "log_file": log_file,
            "json_log_file": json_log_file,
            "platform": platform.system(),
            "python_version": platform.python_version()
        }
    )
    
    return session_logger

def get_logger(name: str, session_id: Optional[str] = None) -> SessionLogger:
    """
    Get a session logger
    
    Args:
        name: Logger name
        session_id: Session ID (uses existing or generates if None)
        
    Returns:
        SessionLogger: Logger with session context
    """
    base_logger = logging.getLogger(name)
    return SessionLogger(base_logger, session_id)

class ActivityLogger:
    """Logs application activities with structured format"""
    
    def __init__(self, logger: SessionLogger, user_id: str = 'anonymous'):
        """
        Initialize the activity logger
        
        Args:
            logger: Session logger
            user_id: User ID
        """
        self.logger = logger
        self.user_id = user_id
        
    def log_job_search(self, job_board: str, query: str, location: str, results_count: int):
        """
        Log a job search activity
        
        Args:
            job_board: Job board name
            query: Search query
            location: Search location
            results_count: Number of results found
        """
        self.logger.log_event(
            "job_search",
            f"Searched for '{query}' in '{location}' on {job_board} - Found {results_count} jobs",
            {
                "job_board": job_board,
                "query": query,
                "location": location,
                "results_count": results_count,
                "user_id": self.user_id
            }
        )
    
    def log_job_analysis(self, job_id: str, job_title: str, match_score: float):
        """
        Log a job analysis activity
        
        Args:
            job_id: Job ID
            job_title: Job title
            match_score: Match score (0-100)
        """
        self.logger.log_event(
            "job_analysis",
            f"Analyzed job {job_title} - Match score: {match_score}",
            {
                "job_id": job_id,
                "job_title": job_title,
                "match_score": match_score,
                "user_id": self.user_id
            }
        )
    
    def log_cover_letter_generation(self, job_id: str, job_title: str, file_path: str):
        """
        Log a cover letter generation activity
        
        Args:
            job_id: Job ID
            job_title: Job title
            file_path: Path to generated cover letter
        """
        self.logger.log_event(
            "cover_letter_generation",
            f"Generated cover letter for {job_title}",
            {
                "job_id": job_id,
                "job_title": job_title,
                "file_path": file_path,
                "user_id": self.user_id
            }
        )
    
    def log_job_application(self, job_id: str, job_title: str, company: str, result: Dict[str, Any]):
        """
        Log a job application activity
        
        Args:
            job_id: Job ID
            job_title: Job title
            company: Company name
            result: Application result
        """
        status = result.get("status", "unknown")
        self.logger.log_event(
            "job_application",
            f"Applied to {job_title} at {company} - Status: {status}",
            {
                "job_id": job_id,
                "job_title": job_title,
                "company": company,
                "status": status,
                "result": result,
                "user_id": self.user_id
            }
        )
    
    def log_browser_action(self, action_type: str, url: str, selector: Optional[str] = None, 
                         description: Optional[str] = None, success: bool = True):
        """
        Log a browser action
        
        Args:
            action_type: Type of action (click, fill, navigate, etc.)
            url: URL of the page
            selector: Element selector (if applicable)
            description: Action description
            success: Whether the action was successful
        """
        self.logger.log_event(
            "browser_action",
            description or f"{action_type.capitalize()} action on {url}",
            {
                "action_type": action_type,
                "url": url,
                "selector": selector,
                "success": success,
                "user_id": self.user_id
            }
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Log an error
        
        Args:
            error: Exception object
            context: Error context
        """
        context = context or {}
        context["user_id"] = self.user_id
        
        self.logger.exception(
            f"Error: {str(error)}",
            extra={"error_context": context}
        )
