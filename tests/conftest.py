# Pytest configuration for AI Job Applicant Bot tests
# Created via MCP GitHub CLI unified tool testing

import pytest
import os
from unittest.mock import Mock

@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration settings"""
    return {
        "openai_api_key": "test-key",
        "test_mode": True,
        "browser_headless": True,
        "log_level": "DEBUG"
    }
    
@pytest.fixture
def mock_browser():
    """Mock browser instance for testing"""
    return Mock()
    
@pytest.fixture
def mock_ai_client():
    """Mock AI client for testing"""
    return Mock()
    
@pytest.fixture
def sample_resume_data():
    """Sample resume data for testing"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "skills": ["Python", "JavaScript", "Machine Learning"],
        "experience": [
            {
                "title": "Senior Developer",
                "company": "Test Company",
                "duration": "2020-2023"
            }
        ],
        "education": [
            {
                "degree": "Computer Science",
                "institution": "Test University",
                "year": "2020"
            }
        ]
    }
    
@pytest.fixture
def sample_job_posting():
    """Sample job posting for testing"""
    return {
        "title": "Senior Software Engineer",
        "company": "Test Tech Company",
        "location": "Remote",
        "salary_range": "$120k-150k",
        "requirements": ["Python", "React", "AWS"],
        "description": "Looking for an experienced software engineer..."
    }
