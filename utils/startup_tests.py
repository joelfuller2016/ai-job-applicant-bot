#!/usr/bin/env python3

"""
Startup Tests

This module provides tests that run at application startup to verify that the system
is properly configured and all dependencies are available.
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
import importlib
import platform
import subprocess
import requests
from dotenv import load_dotenv
from pathlib import Path

from utils.advanced_logging import get_logger

# Load environment variables
load_dotenv()

# Configure logger
logger = get_logger("startup_tests")

class TestResult:
    """Class for storing test results"""
    
    def __init__(self):
        """Initialize test results"""
        self.passed_tests = []
        self.failed_tests = []
        self.skipped_tests = []
        
    def add_passed(self, name: str, message: str = "Test passed"):
        """Add a passed test"""
        self.passed_tests.append({
            "name": name,
            "message": message,
            "status": "passed"
        })
        
    def add_failed(self, name: str, message: str):
        """Add a failed test"""
        self.failed_tests.append({
            "name": name,
            "message": message,
            "status": "failed"
        })
        
    def add_skipped(self, name: str, message: str):
        """Add a skipped test"""
        self.skipped_tests.append({
            "name": name,
            "message": message,
            "status": "skipped"
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of test results"""
        total_tests = len(self.passed_tests) + len(self.failed_tests) + len(self.skipped_tests)
        
        if total_tests == 0:
            success_rate = 0
        else:
            success_rate = int((len(self.passed_tests) / total_tests) * 100)
            
        return {
            "passed": len(self.passed_tests),
            "failed": len(self.failed_tests),
            "skipped": len(self.skipped_tests),
            "total_tests": total_tests,
            "success_rate": success_rate
        }
        
    def get_failed_tests(self) -> List[Dict[str, Any]]:
        """Get a list of failed tests"""
        return self.failed_tests
        
    def get_all_tests(self) -> List[Dict[str, Any]]:
        """Get a list of all tests"""
        return self.passed_tests + self.failed_tests + self.skipped_tests

async def run_all_tests(config_path: str) -> TestResult:
    """
    Run all startup tests
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        TestResult: Test results
    """
    result = TestResult()
    
    # Load configuration
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
        result.add_failed("config", f"Configuration file not found: {config_path}")
        return result
    
    # Test system requirements
    await test_system_requirements(result)
    
    # Test python packages
    await test_python_packages(result)
    
    # Test browser installation
    await test_browser_installation(result)
    
    # Test API keys
    await test_api_keys(result)
    
    # Test browser-use
    await test_browser_use(result)
    
    # Test directories
    await test_directories(result, config)
    
    return result

async def test_system_requirements(result: TestResult):
    """Test system requirements"""
    # Check Python version
    python_version = platform.python_version()
    major, minor, _ = map(int, python_version.split('.'))
    
    if major < 3 or (major == 3 and minor < 11):
        result.add_failed("python_version", f"Python 3.11 or higher is required, but {python_version} is installed")
    else:
        result.add_passed("python_version", f"Python {python_version} is installed")
    
    # Check OS type (not a fail, just informational)
    os_type = platform.system()
    result.add_passed("os_type", f"Operating system: {os_type}")
    
    # Check free disk space
    if os_type == "Windows":
        try:
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p('.'), None, None, ctypes.pointer(free_bytes))
            free_gb = free_bytes.value / (1024**3)
            
            if free_gb < 1.0:
                result.add_failed("disk_space", f"Low disk space: {free_gb:.2f} GB available")
            else:
                result.add_passed("disk_space", f"Disk space: {free_gb:.2f} GB available")
        except:
            result.add_skipped("disk_space", "Could not check disk space on Windows")
    elif os_type in ["Linux", "Darwin"]:
        try:
            import shutil
            total, used, free = shutil.disk_usage('.')
            free_gb = free / (1024**3)
            
            if free_gb < 1.0:
                result.add_failed("disk_space", f"Low disk space: {free_gb:.2f} GB available")
            else:
                result.add_passed("disk_space", f"Disk space: {free_gb:.2f} GB available")
        except:
            result.add_skipped("disk_space", f"Could not check disk space on {os_type}")
    else:
        result.add_skipped("disk_space", f"Disk space check not implemented for {os_type}")
    
    # Check memory
    try:
        import psutil
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        if available_gb < 2.0:
            result.add_failed("memory", f"Low memory: {available_gb:.2f} GB available")
        else:
            result.add_passed("memory", f"Memory: {available_gb:.2f} GB available")
    except ImportError:
        result.add_skipped("memory", "Could not check memory (psutil not installed)")
    except:
        result.add_skipped("memory", "Could not check memory")

async def test_python_packages(result: TestResult):
    """Test required Python packages"""
    required_packages = [
        "browser_use",
        "playwright",
        "streamlit",
        "pandas",
        "numpy",
        "requests",
        "openai",
        "langchain",
        "dotenv"
    ]
    
    for package in required_packages:
        try:
            if package == "dotenv":
                importlib.import_module("dotenv")
            else:
                importlib.import_module(package)
            result.add_passed(f"package_{package}", f"Package {package} is installed")
        except ImportError:
            result.add_failed(f"package_{package}", f"Package {package} is not installed")

async def test_browser_installation(result: TestResult):
    """Test browser installation"""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Check if chromium is installed
            try:
                browser = p.chromium.launch()
                browser.close()
                result.add_passed("browser_chromium", "Chromium browser is installed")
            except Exception as e:
                result.add_failed("browser_chromium", f"Chromium browser is not installed: {e}")
    except ImportError:
        result.add_failed("playwright", "Playwright is not installed")
    except Exception as e:
        result.add_failed("browser_test", f"Browser test failed: {e}")

async def test_api_keys(result: TestResult):
    """Test API keys"""
    # Check OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        result.add_failed("openai_api_key", "OpenAI API key is not set")
    else:
        try:
            # Verify OpenAI API key with a minimal API call
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers
            )
            
            if response.status_code == 200:
                result.add_passed("openai_api_key", "OpenAI API key is valid")
            else:
                result.add_failed("openai_api_key", f"OpenAI API key is invalid: {response.status_code} {response.text}")
        except Exception as e:
            result.add_failed("openai_api_key_test", f"OpenAI API key test failed: {e}")
    
    # Check Anthropic API key (optional)
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        result.add_skipped("anthropic_api_key", "Anthropic API key is not set (optional)")
    else:
        result.add_passed("anthropic_api_key", "Anthropic API key is set")

async def test_browser_use(result: TestResult):
    """Test browser-use installation and functionality"""
    try:
        import browser_use
        result.add_passed("browser_use_import", "browser-use package is installed")
        
        # Check browser-use version
        version = getattr(browser_use, "__version__", "unknown")
        result.add_passed("browser_use_version", f"browser-use version: {version}")
        
        # Check if we can instantiate an Agent (don't actually run it)
        try:
            from browser_use import Agent
            # Just check if the class exists, don't create an instance yet
            result.add_passed("browser_use_agent", "browser-use Agent class is available")
        except Exception as e:
            result.add_failed("browser_use_agent", f"browser-use Agent class is not available: {e}")
            
    except ImportError:
        result.add_failed("browser_use", "browser-use package is not installed")
    except Exception as e:
        result.add_failed("browser_use_test", f"browser-use test failed: {e}")

async def test_directories(result: TestResult, config: Dict[str, Any]):
    """Test necessary directories"""
    required_dirs = [
        "logs",
        "logs/screenshots",
        "resume/data",
        "cover_letters/generated",
        "config",
        "data",
        "data/browser_profiles"
    ]
    
    for directory in required_dirs:
        dir_path = Path(directory)
        if dir_path.exists() and dir_path.is_dir():
            result.add_passed(f"directory_{directory}", f"Directory {directory} exists")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                result.add_passed(f"directory_{directory}", f"Directory {directory} created")
            except Exception as e:
                result.add_failed(f"directory_{directory}", f"Failed to create directory {directory}: {e}")
    
    # Check resume path
    resume_path = config.get("resume_path", "resume/data/resume.json")
    if os.path.exists(resume_path):
        result.add_passed("resume_file", f"Resume file exists: {resume_path}")
    else:
        result.add_skipped("resume_file", f"Resume file does not exist: {resume_path}")

if __name__ == "__main__":
    """Run tests directly"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run startup tests")
    parser.add_argument("--config", default="config/config.json", help="Path to config file")
    args = parser.parse_args()
    
    async def main():
        test_result = await run_all_tests(args.config)
        
        # Print summary
        summary = test_result.get_summary()
        print(f"\nTest Summary:")
        print(f"Passed: {summary['passed']}/{summary['total_tests']} ({summary['success_rate']}%)")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        
        # Print failed tests
        if summary['failed'] > 0:
            print("\nFailed Tests:")
            for test in test_result.get_failed_tests():
                print(f"- {test['name']}: {test['message']}")
        
        return summary['failed'] == 0
    
    # Run the tests
    success = asyncio.run(main())
    
    # Exit with appropriate status
    sys.exit(0 if success else 1)
