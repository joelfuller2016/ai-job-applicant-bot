#!/usr/bin/env python3

"""
Helper Utilities

General utility functions used throughout the application.
"""

import os
import json
import uuid
import hashlib
import time
import random
import string
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load a JSON file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dict containing the JSON data
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        return {}

def save_json_file(data: Dict[str, Any], file_path: str) -> bool:
    """
    Save data to a JSON file
    
    Args:
        data: Data to save
        file_path: Path to the JSON file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        file_dir = os.path.dirname(file_path)
        if file_dir:
            os.makedirs(file_dir, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")
        return False

def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique ID string
    """
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    timestamp = int(time.time())
    unique_id = f"{prefix}{timestamp}_{random_suffix}" if prefix else f"{timestamp}_{random_suffix}"
    return unique_id

def hash_string(text: str) -> str:
    """
    Generate a hash from a string
    
    Args:
        text: Text to hash
        
    Returns:
        Hash string
    """
    return hashlib.md5(text.encode()).hexdigest()

def normalize_string(text: str) -> str:
    """
    Normalize a string (lowercase, remove extra spaces)
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    return " ".join(text.lower().split())

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extract keywords from text
    
    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Remove punctuation
    for char in ".,;:!?()[]{}\"'":
        text = text.replace(char, " ")
    
    # Split into words and filter by length
    words = text.lower().split()
    return [word for word in words if len(word) >= min_length]

def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a path
    
    Args:
        file_path: File path
        
    Returns:
        File extension (lowercase, without the dot)
    """
    return os.path.splitext(file_path)[1].lower()[1:]

def format_date(date_str: str, input_format: str = "%Y-%m-%d", output_format: str = "%B %d, %Y") -> str:
    """
    Format a date string
    
    Args:
        date_str: Date string to format
        input_format: Input date format
        output_format: Output date format
        
    Returns:
        Formatted date string
    """
    try:
        date_obj = datetime.strptime(date_str, input_format)
        return date_obj.strftime(output_format)
    except ValueError:
        logger.error(f"Invalid date format: {date_str}")
        return date_str
    except Exception as e:
        logger.error(f"Error formatting date {date_str}: {e}")
        return date_str

def create_directory_if_not_exists(directory_path: str) -> bool:
    """
    Create a directory if it doesn't exist
    
    Args:
        directory_path: Directory path
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False

def get_random_delay(min_delay: float = 1.0, max_delay: float = 3.0) -> float:
    """
    Get a random delay in seconds
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Random delay in seconds
    """
    return random.uniform(min_delay, max_delay)

def human_readable_time(seconds: int) -> str:
    """
    Convert seconds to human-readable time
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Human-readable time string
    """
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} minutes, {secs} seconds"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} hours, {minutes} minutes"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def safe_get(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Safely get a value from nested dictionaries
    
    Args:
        data: Dictionary to get value from
        keys: List of keys to navigate
        default: Default value if key not found
        
    Returns:
        Value from dictionary or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

def filter_dict(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """
    Filter a dictionary to only include certain keys
    
    Args:
        data: Dictionary to filter
        keys: Keys to include
        
    Returns:
        Filtered dictionary
    """
    return {k: v for k, v in data.items() if k in keys}

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove invalid characters
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscore
    for char in '<>:"/\\|?*':
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(c for c in filename if ord(c) >= 32)
    
    # Trim to reasonable length
    if len(filename) > 200:
        extension = get_file_extension(filename)
        base_name = os.path.splitext(filename)[0]
        filename = f"{base_name[:195]}.{extension}"
    
    return filename

def get_mime_type(file_path: str) -> str:
    """
    Get the MIME type of a file
    
    Args:
        file_path: File path
        
    Returns:
        MIME type string
    """
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"

def format_salary(salary: Union[int, float, str]) -> str:
    """
    Format a salary value
    
    Args:
        salary: Salary value
        
    Returns:
        Formatted salary string
    """
    if isinstance(salary, str):
        try:
            # Try to convert to integer
            salary = int(salary.replace(',', '').replace('$', ''))
        except ValueError:
            # Return as is if conversion fails
            return salary
    
    if isinstance(salary, (int, float)):
        if salary >= 1000:
            # Format as thousands
            return f"${salary:,}"
        else:
            # Assume hourly rate
            return f"${salary:.2f}/hr"
    
    return str(salary)
