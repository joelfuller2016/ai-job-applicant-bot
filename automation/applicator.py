#!/usr/bin/env python3

"""
Job Application Automation

This module handles automated job applications using Playwright.
"""

import os
import re
import time
import json
import logging
import random
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

from automation.job_search import JobPost
from resume.parser import ResumeParser

logger = logging.getLogger(__name__)

class ApplicationFormField:
    """Represents a field in a job application form"""
    
    def __init__(self, 
                 field_type: str,
                 selector: str,
                 label: Optional[str] = None,
                 name: Optional[str] = None,
                 id: Optional[str] = None,
                 value: Optional[str] = None,
                 options: Optional[List[str]] = None,
                 required: bool = False):
        """
        Initialize a form field
        
        Args:
            field_type: Type of field (text, select, radio, checkbox, textarea, file)
            selector: CSS selector for the field
            label: Field label text (optional)
            name: Field name attribute (optional)
            id: Field ID attribute (optional)
            value: Field value (optional)
            options: List of options for select, radio, or checkbox fields (optional)
            required: Whether the field is required (optional)
        """
        self.field_type = field_type
        self.selector = selector
        self.label = label
        self.name = name
        self.id = id
        self.value = value
        self.options = options or []
        self.required = required
        
    def __str__(self) -> str:
        """String representation of the field"""
        label_str = f" '{self.label}'" if self.label else ""
        return f"{self.field_type.capitalize()} field{label_str}"


class ApplicationSystem:
    """Base class for various application tracking systems (ATS)"""
    
    def __init__(self, page: Page, resume_parser: ResumeParser, job: JobPost):
        """
        Initialize the ATS handler
        
        Args:
            page: Playwright page object
            resume_parser: Parser with parsed resume data
            job: Job posting to apply for
        """
        self.page = page
        self.resume_parser = resume_parser
        self.resume_data = resume_parser.get_parsed_data()
        self.job = job
        
    def detect_and_fill_form(self) -> bool:
        """
        Detect form fields and fill them with appropriate values
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Detect form fields
            fields = self._detect_form_fields()
            
            if not fields:
                logger.warning("No form fields detected")
                return False
            
            logger.info(f"Detected {len(fields)} form fields")
            
            # Fill each field
            for field in fields:
                self._fill_field(field)
                
                # Add a small delay to appear more human-like
                time.sleep(random.uniform(0.5, 1.5))
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling application form: {e}")
            return False
    
    def _detect_form_fields(self) -> List[ApplicationFormField]:
        """
        Detect form fields on the page
        
        Returns:
            List of ApplicationFormField objects
        """
        fields = []
        
        # Look for input fields
        input_selectors = [
            "input[type='text']",
            "input[type='email']",
            "input[type='tel']",
            "input[type='number']",
            "input[type='url']",
            "textarea",
            "select",
            "input[type='radio']",
            "input[type='checkbox']",
            "input[type='file']"
        ]
        
        # Combine all selectors
        combined_selector = ", ".join(input_selectors)
        
        # Get all form elements
        form_elements = self.page.query_selector_all(combined_selector)
        
        for element in form_elements:
            # Get element attributes
            tag_name = element.evaluate("el => el.tagName.toLowerCase()")
            element_type = element.get_attribute("type") if tag_name == "input" else tag_name
            name = element.get_attribute("name")
            id = element.get_attribute("id")
            label_text = self._get_field_label(element)
            
            # Check if the field is required
            required = element.get_attribute("required") is not None or element.get_attribute("aria-required") == "true"
            
            # Create field object based on type
            if element_type in ["text", "email", "tel", "number", "url"]:
                field = ApplicationFormField(
                    field_type="text",
                    selector=f"#{id}" if id else f"[name='{name}']" if name else "",
                    label=label_text,
                    name=name,
                    id=id,
                    required=required
                )
                fields.append(field)
                
            elif element_type == "textarea":
                field = ApplicationFormField(
                    field_type="textarea",
                    selector=f"#{id}" if id else f"[name='{name}']" if name else "textarea",
                    label=label_text,
                    name=name,
                    id=id,
                    required=required
                )
                fields.append(field)
                
            elif element_type == "select":
                # Get options
                options = element.evaluate("""el => {
                    return Array.from(el.options).map(option => option.text);
                }""")
                
                field = ApplicationFormField(
                    field_type="select",
                    selector=f"#{id}" if id else f"[name='{name}']" if name else "select",
                    label=label_text,
                    name=name,
                    id=id,
                    options=options,
                    required=required
                )
                fields.append(field)
                
            elif element_type == "radio":
                # Group radio buttons by name
                group_name = name or ""
                
                # Check if this radio group is already added
                if not any(f.field_type == "radio" and f.name == group_name for f in fields):
                    # Get all options for this radio group
                    options = self.page.evaluate(f"""() => {{
                        const radios = document.querySelectorAll('input[type="radio"][name="{group_name}"]');
                        return Array.from(radios).map(radio => {{
                            const label = radio.labels[0];
                            return label ? label.textContent.trim() : radio.value;
                        }});
                    }}""")
                    
                    field = ApplicationFormField(
                        field_type="radio",
                        selector=f"input[type='radio'][name='{group_name}']",
                        label=label_text,
                        name=group_name,
                        options=options,
                        required=required
                    )
                    fields.append(field)
                
            elif element_type == "checkbox":
                field = ApplicationFormField(
                    field_type="checkbox",
                    selector=f"#{id}" if id else f"[name='{name}']" if name else "",
                    label=label_text,
                    name=name,
                    id=id,
                    required=required
                )
                fields.append(field)
                
            elif element_type == "file":
                field = ApplicationFormField(
                    field_type="file",
                    selector=f"#{id}" if id else f"[name='{name}']" if name else "input[type='file']",
                    label=label_text,
                    name=name,
                    id=id,
                    required=required
                )
                fields.append(field)
        
        return fields
    
    def _get_field_label(self, element) -> Optional[str]:
        """Get the label text for a form field"""
        # Try to find label by for attribute first
        element_id = element.get_attribute("id")
        if element_id:
            label_element = self.page.query_selector(f"label[for='{element_id}']")
            if label_element:
                return label_element.inner_text().strip()
        
        # Try to find parent label
        label_text = element.evaluate("""el => {
            const closestLabel = el.closest('label');
            if (closestLabel) {
                return closestLabel.textContent.trim();
            }
            return null;
        }""")
        
        if label_text:
            return label_text
        
        # Try placeholder
        placeholder = element.get_attribute("placeholder")
        if placeholder:
            return placeholder
        
        # Try aria-label
        aria_label = element.get_attribute("aria-label")
        if aria_label:
            return aria_label
        
        # Try name attribute with formatting
        name = element.get_attribute("name")
        if name:
            # Convert camelCase or snake_case to spaces
            formatted_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)  # camelCase
            formatted_name = re.sub(r'_+', ' ', formatted_name)  # snake_case
            return formatted_name.strip().capitalize()
        
        return None
    
    def _fill_field(self, field: ApplicationFormField) -> bool:
        """
        Fill a form field with the appropriate value
        
        Args:
            field: ApplicationFormField to fill
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not field.selector:
                logger.warning(f"No selector for field: {field}")
                return False
            
            # Wait for the field to be visible
            self.page.wait_for_selector(field.selector, state="visible", timeout=5000)
            
            # Determine the appropriate value based on field label/name
            value = self._determine_field_value(field)
            
            # Fill based on field type
            if field.field_type == "text":
                self.page.fill(field.selector, value)
                logger.debug(f"Filled text field {field.label or field.name}: {value}")
                
            elif field.field_type == "textarea":
                self.page.fill(field.selector, value)
                logger.debug(f"Filled textarea {field.label or field.name}")
                
            elif field.field_type == "select":
                if value in field.options:
                    self.page.select_option(field.selector, value)
                else:
                    # Try to find a close match
                    for option in field.options:
                        if value.lower() in option.lower() or option.lower() in value.lower():
                            self.page.select_option(field.selector, option)
                            break
                    else:
                        # If no match, select the first non-empty option
                        for option in field.options:
                            if option.strip():
                                self.page.select_option(field.selector, option)
                                break
                logger.debug(f"Selected option for {field.label or field.name}")
                
            elif field.field_type == "radio":
                # Convert string value to 0-based index for selectOption
                if value in field.options:
                    index = field.options.index(value)
                    radio_selector = f"{field.selector}:nth-of-type({index + 1})"
                    self.page.check(radio_selector)
                else:
                    # Default to first option if value doesn't match
                    radio_selector = f"{field.selector}:first-of-type"
                    self.page.check(radio_selector)
                logger.debug(f"Selected radio option for {field.label or field.name}")
                
            elif field.field_type == "checkbox":
                if value.lower() in ["yes", "true", "1"]:
                    self.page.check(field.selector)
                logger.debug(f"Set checkbox {field.label or field.name}: {value}")
                
            elif field.field_type == "file":
                # Check if the field requires a resume
                if field.label and "resume" in (field.label or "").lower():
                    # Get resume path and validate
                    resume_paths = list(Path('resume/data').glob('*.pdf'))
                    if resume_paths:
                        resume_path = str(resume_paths[0].absolute())
                        self.page.set_input_files(field.selector, resume_path)
                        logger.debug(f"Uploaded resume: {resume_path}")
                    else:
                        logger.warning("No resume file found in resume/data directory")
                        return False
                else:
                    logger.warning(f"Unknown file upload field: {field.label or field.name}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling field {field.label or field.name}: {e}")
            return False
    
    def _determine_field_value(self, field: ApplicationFormField) -> str:
        """
        Determine the appropriate value for a field based on its label/name
        
        Args:
            field: ApplicationFormField to determine value for
            
        Returns:
            str: Appropriate value for the field
        """
        label = (field.label or "").lower()
        name = (field.name or "").lower()
        
        # Common field mappings
        field_mappings = {
            # Personal information
            "name": self.resume_data['contact_info'].get('name', ''),
            "first name": self.resume_data['contact_info'].get('name', '').split()[0] if self.resume_data['contact_info'].get('name') else '',
            "last name": self.resume_data['contact_info'].get('name', '').split()[-1] if self.resume_data['contact_info'].get('name') and len(self.resume_data['contact_info'].get('name', '').split()) > 1 else '',
            "email": self.resume_data['contact_info'].get('email', ''),
            "phone": self.resume_data['contact_info'].get('phone', ''),
            "address": self.resume_data['contact_info'].get('location', ''),
            "location": self.resume_data['contact_info'].get('location', ''),
            "city": self.resume_data['contact_info'].get('location', '').split(',')[0] if ',' in self.resume_data['contact_info'].get('location', '') else '',
            "state": self.resume_data['contact_info'].get('location', '').split(',')[-1].strip() if ',' in self.resume_data['contact_info'].get('location', '') else '',
            "zip": "",  # Not easily extractable from basic location
            "linkedin": self.resume_data['contact_info'].get('linkedin', ''),
            "github": self.resume_data['contact_info'].get('github', ''),
            
            # Experience
            "years of experience": str(int(self.resume_parser.get_experience_years())),
            "experience": str(int(self.resume_parser.get_experience_years())),
            
            # Education
            "education": ", ".join([f"{edu.get('degree', '')} from {edu.get('institution', '')}" for edu in self.resume_data.get('education', [])]),
            "degree": self.resume_data.get('education', [{}])[0].get('degree', '') if self.resume_data.get('education') else '',
            
            # Skills
            "skills": ", ".join(self.resume_data.get('skills', [])[:10]),
            
            # Other common fields
            "salary": "Negotiable",
            "salary expectations": "Negotiable",
            "expected salary": "Negotiable",
            "desired salary": "Negotiable",
            "start date": "Immediate",
            "availability": "2 weeks notice",
            "relocate": "No",
            "willing to relocate": "No",
            "work authorization": "Yes",
            "authorized to work": "Yes",
            "citizenship": "U.S. Citizen",
            "visa": "Not Required",
            "sponsorship": "No",
            "require sponsorship": "No",
            "reference": "Available upon request",
            "references": "Available upon request",
            "hear about us": "Job board",
            "how did you hear": "Job board",
            "source": "Job board",
            
            # Cover letter or additional information
            "cover letter": self._generate_short_cover_letter(),
            "additional information": self._generate_additional_info(),
            "why do you want to work here": self._generate_why_work_here(),
            "why should we hire you": self._generate_why_hire_me()
        }
        
        # Check for matches in label or name
        for key, value in field_mappings.items():
            if key in label or key in name:
                return value
        
        # If no specific match, use some heuristics
        if "name" in label or "name" in name:
            return self.resume_data['contact_info'].get('name', '')
        
        if field.field_type == "textarea":
            return self._generate_additional_info()
        
        # Default empty string for unknown fields
        return ""
    
    def _generate_short_cover_letter(self) -> str:
        """Generate a short cover letter"""
        return f"""Dear Hiring Manager,

I am excited to apply for the {self.job.title} position at {self.job.company}. With {int(self.resume_parser.get_experience_years())} years of experience and a strong background in {', '.join(self.resume_data.get('skills', [])[:3])}, I believe I would be a valuable addition to your team.

My experience aligns well with the requirements in your job description, and I am particularly drawn to the opportunity to work on {self.job.company}'s innovative projects.

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and experience can contribute to your team's success.

Sincerely,
{self.resume_data['contact_info'].get('name', '')}"""
    
    def _generate_additional_info(self) -> str:
        """Generate additional information for open-ended questions"""
        skills = ', '.join(self.resume_data.get('skills', [])[:5])
        return f"I have {int(self.resume_parser.get_experience_years())} years of experience in software development with expertise in {skills}. I am seeking a remote position where I can contribute my skills to a dynamic team."
    
    def _generate_why_work_here(self) -> str:
        """Generate response for 'Why do you want to work here?'"""
        return f"I'm impressed by {self.job.company}'s reputation and the innovative work you're doing. The {self.job.title} role aligns perfectly with my skills and career goals. I'm particularly excited about the opportunity to work in a remote environment while contributing to meaningful projects."
    
    def _generate_why_hire_me(self) -> str:
        """Generate response for 'Why should we hire you?'"""
        return f"My {int(self.resume_parser.get_experience_years())} years of experience in software development, combined with my expertise in {', '.join(self.resume_data.get('skills', [])[:3])}, make me well-suited for this role. I have a proven track record of delivering high-quality solutions and working effectively in remote teams."


class GenericATS(ApplicationSystem):
    """General ATS implementation for most application systems"""
    
    def apply(self) -> bool:
        """
        Apply to the job
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Navigate to the job application page
            self.page.goto(self.job.apply_url)
            logger.info(f"Navigated to application page: {self.job.apply_url}")
            
            # Wait for page to load
            self.page.wait_for_load_state("networkidle")
            
            # Look for an "Apply" button if not already on application form
            self._click_apply_button()
            
            # Detect and fill the application form
            if not self.detect_and_fill_form():
                logger.warning("Failed to fill application form")
                return False
            
            # Look for and click the submit button (but don't actually submit in this demo)
            submit_button = self._find_submit_button()
            if submit_button:
                logger.info("Found submit button - would click in production version")
                
                # In a real implementation, would uncomment this:
                # submit_button.click()
                # self.page.wait_for_load_state("networkidle")
                # logger.info("Application submitted successfully")
                
                return True
            else:
                logger.warning("Could not find submit button")
                return False
            
        except Exception as e:
            logger.error(f"Error applying to job: {e}")
            return False
    
    def _click_apply_button(self) -> bool:
        """
        Find and click the Apply button if present
        
        Returns:
            bool: True if button found and clicked, False otherwise
        """
        # Common selectors for apply buttons
        apply_button_selectors = [
            "a:has-text('Apply')",
            "button:has-text('Apply')",
            "input[type='button'][value*='Apply']",
            ".apply-button",
            "[data-test='apply-button']",
            "[aria-label*='Apply']",
            "[title*='Apply']"
        ]
        
        # Try each selector
        for selector in apply_button_selectors:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    button.click()
                    logger.info(f"Clicked apply button with selector: {selector}")
                    
                    # Wait for navigation
                    self.page.wait_for_load_state("networkidle")
                    return True
            except Exception as e:
                logger.debug(f"No apply button found with selector {selector}: {e}")
        
        logger.info("No apply button found, may already be on application form")
        return False
    
    def _find_submit_button(self):
        """
        Find the submit button on the application form
        
        Returns:
            ElementHandle or None: Submit button element if found, None otherwise
        """
        # Common selectors for submit buttons
        submit_button_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')",
            "a:has-text('Submit')",
            "a:has-text('Apply')",
            ".submit-button",
            "[data-test='submit-button']",
            "[aria-label*='Submit']",
            "[aria-label*='Apply']"
        ]
        
        # Try each selector
        for selector in submit_button_selectors:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    logger.info(f"Found submit button with selector: {selector}")
                    return button
            except Exception:
                pass
        
        return None


class GreenhouseATS(ApplicationSystem):
    """Specific implementation for Greenhouse ATS"""
    
    def apply(self) -> bool:
        """Apply to job on Greenhouse ATS"""
        try:
            # Navigate to the job application page
            self.page.goto(self.job.apply_url)
            logger.info(f"Navigated to Greenhouse application page: {self.job.apply_url}")
            
            # Wait for page to load
            self.page.wait_for_load_state("networkidle")
            
            # Fill the first name
            self.page.fill("#first_name", self.resume_data['contact_info'].get('name', '').split()[0])
            
            # Fill the last name
            last_name = self.resume_data['contact_info'].get('name', '').split()[-1] if len(self.resume_data['contact_info'].get('name', '').split()) > 1 else ''
            self.page.fill("#last_name", last_name)
            
            # Fill the email
            self.page.fill("#email", self.resume_data['contact_info'].get('email', ''))
            
            # Fill the phone
            self.page.fill("#phone", self.resume_data['contact_info'].get('phone', ''))
            
            # Upload resume if field exists
            resume_upload = self.page.query_selector("#resume_fieldset input[type='file']")
            if resume_upload:
                resume_paths = list(Path('resume/data').glob('*.pdf'))
                if resume_paths:
                    resume_path = str(resume_paths[0].absolute())
                    self.page.set_input_files("#resume_fieldset input[type='file']", resume_path)
                    logger.debug(f"Uploaded resume: {resume_path}")
            
            # Fill cover letter if field exists
            cover_letter_field = self.page.query_selector("#cover_letter_text")
            if cover_letter_field:
                self.page.fill("#cover_letter_text", self._generate_short_cover_letter())
            
            # Fill additional custom fields
            self.detect_and_fill_form()
            
            # Find and click submit button (but don't actually submit in this demo)
            submit_button = self.page.query_selector("#submit_app")
            if submit_button:
                logger.info("Found submit button - would click in production version")
                
                # In a real implementation, would uncomment this:
                # submit_button.click()
                # self.page.wait_for_load_state("networkidle")
                # logger.info("Application submitted successfully")
                
                return True
            else:
                logger.warning("Could not find submit button")
                return False
            
        except Exception as e:
            logger.error(f"Error applying to job on Greenhouse: {e}")
            return False


class LeverATS(ApplicationSystem):
    """Specific implementation for Lever ATS"""
    
    def apply(self) -> bool:
        """Apply to job on Lever ATS"""
        try:
            # Navigate to the job application page
            self.page.goto(self.job.apply_url)
            logger.info(f"Navigated to Lever application page: {self.job.apply_url}")
            
            # Wait for page to load
            self.page.wait_for_load_state("networkidle")
            
            # Fill the name
            self.page.fill("input[name='name']", self.resume_data['contact_info'].get('name', ''))
            
            # Fill the email
            self.page.fill("input[name='email']", self.resume_data['contact_info'].get('email', ''))
            
            # Fill the phone
            phone_field = self.page.query_selector("input[name='phone']")
            if phone_field:
                self.page.fill("input[name='phone']", self.resume_data['contact_info'].get('phone', ''))
            
            # Fill company
            company_field = self.page.query_selector("input[name='org']")
            if company_field:
                # Get most recent company from experience
                company = self.resume_data.get('experience', [{}])[0].get('company', '') if self.resume_data.get('experience') else ''
                self.page.fill("input[name='org']", company)
            
            # Upload resume
            resume_upload = self.page.query_selector("input[name='resume']")
            if resume_upload:
                resume_paths = list(Path('resume/data').glob('*.pdf'))
                if resume_paths:
                    resume_path = str(resume_paths[0].absolute())
                    self.page.set_input_files("input[name='resume']", resume_path)
                    logger.debug(f"Uploaded resume: {resume_path}")
            
            # Fill cover letter if field exists
            cover_letter_field = self.page.query_selector("textarea[name='comments']")
            if cover_letter_field:
                self.page.fill("textarea[name='comments']", self._generate_short_cover_letter())
            
            # Fill LinkedIn URL if field exists
            linkedin_field = self.page.query_selector("input[name='urls[LinkedIn]']")
            if linkedin_field:
                self.page.fill("input[name='urls[LinkedIn]']", self.resume_data['contact_info'].get('linkedin', ''))
            
            # Fill GitHub URL if field exists
            github_field = self.page.query_selector("input[name='urls[GitHub]']")
            if github_field:
                self.page.fill("input[name='urls[GitHub]']", self.resume_data['contact_info'].get('github', ''))
            
            # Fill additional custom fields
            self.detect_and_fill_form()
            
            # Find and click submit button (but don't actually submit in this demo)
            submit_button = self.page.query_selector("button[type='submit']")
            if submit_button:
                logger.info("Found submit button - would click in production version")
                
                # In a real implementation, would uncomment this:
                # submit_button.click()
                # self.page.wait_for_load_state("networkidle")
                # logger.info("Application submitted successfully")
                
                return True
            else:
                logger.warning("Could not find submit button")
                return False
            
        except Exception as e:
            logger.error(f"Error applying to job on Lever: {e}")
            return False


class ApplicationAutomator:
    """Manages automated job applications across different ATS platforms"""
    
    def __init__(self, config: Dict[str, Any], resume_parser: ResumeParser):
        """
        Initialize the application automator
        
        Args:
            config: Configuration dictionary
            resume_parser: ResumeParser instance with parsed resume
        """
        self.config = config
        self.resume_parser = resume_parser
        self.browser = None
        self.page = None
        self.application_results = []
        
    def __enter__(self):
        """Initialize the browser"""
        self._initialize_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the browser"""
        self._close_browser()
    
    def _initialize_browser(self):
        """Initialize the Playwright browser"""
        try:
            logger.info("Initializing browser...")
            
            playwright = sync_playwright().start()
            
            # Launch browser
            self.browser = playwright.chromium.launch(
                headless=False,  # Set to True in production
                slow_mo=50  # Slow down operations for visualization
            )
            
            # Create a new context with realistic viewport
            context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # Create a new page
            self.page = context.new_page()
            
            # Set default timeout
            self.page.set_default_timeout(30000)
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            self._close_browser()
    
    def _close_browser(self):
        """Close the Playwright browser"""
        try:
            if self.browser:
                self.browser.close()
                logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    def apply_to_job(self, job: JobPost) -> bool:
        """
        Apply to a single job
        
        Args:
            job: JobPost to apply for
            
        Returns:
            bool: True if application was successful, False otherwise
        """
        if not self.browser or not self.page:
            logger.error("Browser not initialized")
            return False
        
        try:
            logger.info(f"Applying to job: {job.title} at {job.company}")
            
            # Detect ATS type
            ats_type = self._detect_ats_type(job.apply_url)
            logger.info(f"Detected ATS type: {ats_type}")
            
            # Create appropriate ATS handler
            if ats_type == "greenhouse":
                ats = GreenhouseATS(self.page, self.resume_parser, job)
            elif ats_type == "lever":
                ats = LeverATS(self.page, self.resume_parser, job)
            else:
                ats = GenericATS(self.page, self.resume_parser, job)
            
            # Apply to the job
            result = ats.apply()
            
            if result:
                logger.info(f"Successfully applied to {job.title} at {job.company}")
            else:
                logger.warning(f"Failed to apply to {job.title} at {job.company}")
            
            # Record result
            self.application_results.append({
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company,
                "apply_url": job.apply_url,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "success": result,
                "ats_type": ats_type
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying to job: {e}")
            
            # Record failure
            self.application_results.append({
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company,
                "apply_url": job.apply_url,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "success": False,
                "error": str(e),
                "ats_type": "unknown"
            })
            
            return False
    
    def _detect_ats_type(self, url: str) -> str:
        """
        Detect the ATS type based on the URL
        
        Args:
            url: Job application URL
            
        Returns:
            str: ATS type ("greenhouse", "lever", "workday", "taleo", or "generic")
        """
        if "greenhouse.io" in url:
            return "greenhouse"
        elif "lever.co" in url:
            return "lever"
        elif "myworkdayjobs.com" in url or "workday.com" in url:
            return "workday"
        elif "taleo.net" in url:
            return "taleo"
        else:
            # Navigate to the page and try to detect based on content
            try:
                self.page.goto(url)
                self.page.wait_for_load_state("networkidle")
                
                # Check for Greenhouse
                if self.page.query_selector("#submit_app") or self.page.query_selector("#greenhouse-forms"):
                    return "greenhouse"
                
                # Check for Lever
                if self.page.query_selector(".lever-job-title") or self.page.query_selector("[data-qa='btn-apply-bottom']"):
                    return "lever"
                
                # Check for Workday
                if "workday" in self.page.content().lower() or "myworkday" in self.page.content().lower():
                    return "workday"
                
                # Check for Taleo
                if "taleo" in self.page.content().lower():
                    return "taleo"
                
            except Exception as e:
                logger.warning(f"Error detecting ATS type: {e}")
            
            return "generic"
    
    def apply_to_jobs(self, jobs: List[JobPost], limit: int = None) -> List[Dict[str, Any]]:
        """
        Apply to multiple jobs
        
        Args:
            jobs: List of JobPost objects to apply to
            limit: Maximum number of jobs to apply to (optional)
            
        Returns:
            List of application results
        """
        if not self.browser or not self.page:
            self._initialize_browser()
        
        applied_count = 0
        
        # Apply to each job
        for job in jobs:
            # Check if we've reached the limit
            if limit and applied_count >= limit:
                logger.info(f"Reached application limit of {limit}")
                break
            
            # Apply to the job
            success = self.apply_to_job(job)
            
            if success:
                applied_count += 1
            
            # Random delay between applications to seem more human-like
            time.sleep(random.uniform(2, 5))
        
        logger.info(f"Applied to {applied_count} jobs")
        return self.application_results
    
    def save_application_results(self, output_path: str = "logs/application_results.json"):
        """
        Save application results to a file
        
        Args:
            output_path: Path to save results to
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w") as f:
                json.dump(self.application_results, f, indent=2)
                
            logger.info(f"Saved application results to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving application results: {e}")


# Console runner for testing
def run_console_mode(config_path: str):
    """
    Run application automation in console mode
    
    Args:
        config_path: Path to config file
    """
    from automation.job_search import JobSearchManager
    from resume.parser import ResumeParser, get_resume_files
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Check for resume files
    resume_files = get_resume_files()
    if not resume_files:
        logger.error("No resume files found in resume/data/ directory")
        return
    
    # Parse resume
    resume_parser = ResumeParser(resume_files[0])
    
    # Initialize job search manager
    job_search = JobSearchManager(config)
    
    # Search for jobs
    new_jobs = job_search.search_all_job_boards()
    logger.info(f"Found {len(new_jobs)} new jobs")
    
    # Get all jobs
    all_jobs = job_search.get_all_jobs()
    logger.info(f"Total jobs in database: {len(all_jobs)}")
    
    # Sort jobs by title
    all_jobs.sort(key=lambda j: j.title)
    
    # Print jobs
    for i, job in enumerate(all_jobs[:10]):  # Show first 10
        print(f"{i+1}. {job.title} at {job.company} ({job.location}) - {job.job_board}")
    
    if len(all_jobs) > 10:
        print(f"...and {len(all_jobs) - 10} more")
    
    # Ask if user wants to apply
    response = input("\nDo you want to apply to these jobs? (y/n): ")
    if response.lower() != 'y':
        print("Exiting without applying")
        return
    
    # Ask for limit
    try:
        limit = int(input("How many jobs do you want to apply to? (default: 3): ") or "3")
    except ValueError:
        limit = 3
    
    # Initialize application automator
    with ApplicationAutomator(config, resume_parser) as automator:
        # Apply to jobs
        results = automator.apply_to_jobs(all_jobs, limit=limit)
        
        # Save results
        automator.save_application_results()
    
    # Print results
    print("\nApplication Results:")
    for result in results:
        status = "Success" if result['success'] else "Failed"
        print(f"{status}: {result['job_title']} at {result['company']} ({result['ats_type']})")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    from resume.parser import ResumeParser, get_resume_files
    
    # Check for resume files
    resume_files = get_resume_files()
    
    if not resume_files:
        logger.error("No resume files found in resume/data/ directory")
    else:
        # Parse resume
        resume_parser = ResumeParser(resume_files[0])
        
        # Create a sample job
        from automation.job_search import JobPost
        
        job = JobPost(
            title="Senior Software Engineer",
            company="Example Corp",
            location="Remote",
            description="This is a sample job description...",
            url="https://example.com/jobs/123",
            job_board="Example",
            date_posted="2025-04-01",
            job_type="Full-time"
        )
        
        # Initialize application automator and apply
        with ApplicationAutomator({}, resume_parser) as automator:
            # This will print debug messages showing what would happen without actually submitting
            automator.apply_to_job(job)
