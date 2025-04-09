#!/usr/bin/env python3

"""
Cover Letter Generator

Generates customized cover letters based on resume and job data using templates.
"""

import os
import re
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import jinja2

from automation.job_search import JobPost

logger = logging.getLogger(__name__)

class CoverLetterGenerator:
    """Generates customized cover letters"""
    
    def __init__(self, resume_data: Dict[str, Any], template_dir: str = 'cover_letters/templates'):
        """
        Initialize the cover letter generator
        
        Args:
            resume_data: Parsed resume data
            template_dir: Directory containing templates
        """
        self.resume_data = resume_data
        self.template_dir = template_dir
        self.output_dir = 'cover_letters/generated'
        
        # Create output directory if it doesn't exist
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create template directory if it doesn't exist
        template_path = Path(template_dir)
        template_path.mkdir(parents=True, exist_ok=True)
        
        # Create default template if none exists
        default_template_path = template_path / 'default.txt'
        if not default_template_path.exists():
            self._create_default_template(default_template_path)
        
        # Initialize Jinja environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def _create_default_template(self, template_path: Path):
        """Create a default cover letter template"""
        default_template = """{{ user_name }}
{{ user_email }}
{{ user_phone }}
{{ user_location }}

{{ date }}

{{ company_name }}
{{ company_address|default('') }}

Dear Hiring Manager,

I am writing to express my interest in the {{ job_title }} position at {{ company_name }}. With {{ experience_years }} years of experience in software development and a strong background in {{ skills|join(', ') }}, I am confident in my ability to make a valuable contribution to your team.

{% if job_description %}
Based on the job description, I understand you are looking for someone with expertise in {{ job_skills|join(', ') }}. Throughout my career, I have:
{% else %}
Throughout my career, I have:
{% endif %}

- Developed and maintained numerous software applications using {{ skills[:3]|join(', ') }}
- Collaborated effectively with cross-functional teams to deliver high-quality solutions
- Continuously learned and adapted to new technologies and methodologies

{% if matching_strengths %}
My particular strengths relevant to this role include {{ matching_strengths|join(', ') }}.
{% endif %}

I am drawn to {{ company_name }} because of your reputation for {{ company_values|default('innovation and excellence') }}. I am particularly excited about the opportunity to work on {{ company_projects|default('challenging projects') }} and contribute to your continued success.

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and experience align with your needs. Please feel free to contact me at {{ user_phone }} or {{ user_email }} to arrange a conversation.

Sincerely,
{{ user_name }}
"""
        
        # Write the template to file
        with open(template_path, 'w') as f:
            f.write(default_template)
        
        logger.info(f"Created default cover letter template at {template_path}")
    
    def generate_cover_letter(self, job: JobPost, match_data: Dict[str, Any] = None, 
                            template_name: str = 'default.txt') -> str:
        """
        Generate a cover letter for a specific job
        
        Args:
            job: JobPost object
            match_data: Data from job matching (optional)
            template_name: Name of the template to use
            
        Returns:
            str: Generated cover letter text
        """
        try:
            # Load the template
            template = self.env.get_template(template_name)
            
            # Prepare context data for the template
            context = self._prepare_context(job, match_data)
            
            # Render the template
            cover_letter = template.render(**context)
            
            logger.info(f"Generated cover letter for {job.title} at {job.company}")
            
            return cover_letter
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            
            # Return a simple cover letter as fallback
            return self._generate_fallback_cover_letter(job)
    
    def _prepare_context(self, job: JobPost, match_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Prepare context data for template rendering
        
        Args:
            job: JobPost object
            match_data: Data from job matching (optional)
            
        Returns:
            Dict[str, Any]: Context data for template rendering
        """
        # Get current date
        today = datetime.datetime.now().strftime('%B %d, %Y')
        
        # Extract user info from resume data
        contact_info = self.resume_data.get('contact_info', {})
        user_name = contact_info.get('name', '')
        user_email = contact_info.get('email', '')
        user_phone = contact_info.get('phone', '')
        user_location = contact_info.get('location', '')
        
        # Extract skills from resume data
        skills = self.resume_data.get('skills', [])
        
        # Extract experience years (approximate)
        experience_years = "several"
        experience_data = self.resume_data.get('experience', [])
        if experience_data:
            # Count years from experience entries
            total_years = 0
            for exp in experience_data:
                start = exp.get('start_date', '')
                end = exp.get('end_date', '')
                
                # Extract years using regex
                start_year = self._extract_year(start)
                end_year = self._extract_year(end) if end.lower() not in ['present', 'current'] else datetime.datetime.now().year
                
                if start_year and end_year:
                    total_years += end_year - start_year
            
            if total_years > 0:
                experience_years = f"{int(total_years)}"
        
        # Extract job skills from job description
        job_skills = []
        if match_data and 'job_skills' in match_data:
            job_skills = match_data.get('job_skills', [])
        
        # Extract matching strengths
        matching_strengths = []
        if match_data and 'strengths' in match_data:
            matching_strengths = match_data.get('strengths', [])
        
        # Construct context dictionary
        context = {
            'date': today,
            'user_name': user_name,
            'user_email': user_email,
            'user_phone': user_phone,
            'user_location': user_location,
            'job_title': job.title,
            'company_name': job.company,
            'company_address': '',  # Not available in JobPost
            'job_description': job.description,
            'skills': skills,
            'job_skills': job_skills,
            'experience_years': experience_years,
            'matching_strengths': matching_strengths,
            'company_values': 'innovation and excellence in the industry',  # Default values
            'company_projects': 'challenging and impactful projects'  # Default values
        }
        
        return context
    
    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from a date string"""
        year_match = re.search(r'(19|20)\d{2}', date_str)
        if year_match:
            return int(year_match.group(0))
        return None
    
    def _generate_fallback_cover_letter(self, job: JobPost) -> str:
        """Generate a simple fallback cover letter"""
        # Get current date
        today = datetime.datetime.now().strftime('%B %d, %Y')
        
        # Extract user info
        contact_info = self.resume_data.get('contact_info', {})
        user_name = contact_info.get('name', 'Your Name')
        user_email = contact_info.get('email', 'your.email@example.com')
        user_phone = contact_info.get('phone', '(123) 456-7890')
        
        # Create a simple cover letter
        cover_letter = f"""{user_name}
{user_email}
{user_phone}

{today}

{job.company}

Dear Hiring Manager,

I am writing to express my interest in the {job.title} position at {job.company}. I believe my skills and experience make me a strong candidate for this role.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team.

Sincerely,
{user_name}
"""
        
        return cover_letter
    
    def save_cover_letter_txt(self, cover_letter: str, job: JobPost) -> str:
        """
        Save cover letter as a text file
        
        Args:
            cover_letter: Cover letter text
            job: JobPost object
            
        Returns:
            str: Path to saved file
        """
        # Create a safe filename
        company_name = re.sub(r'[^\w\s-]', '', job.company).strip().replace(' ', '-').lower()
        position_name = re.sub(r'[^\w\s-]', '', job.title).strip().replace(' ', '-').lower()
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        
        filename = f"{company_name}-{position_name}-{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        # Write to file
        with open(filepath, 'w') as f:
            f.write(cover_letter)
        
        logger.info(f"Saved cover letter to {filepath}")
        
        return filepath
    
    def save_cover_letter_docx(self, cover_letter: str, job: JobPost) -> str:
        """
        Save cover letter as a Word document
        
        Args:
            cover_letter: Cover letter text
            job: JobPost object
            
        Returns:
            str: Path to saved file
        """
        # Create a safe filename
        company_name = re.sub(r'[^\w\s-]', '', job.company).strip().replace(' ', '-').lower()
        position_name = re.sub(r'[^\w\s-]', '', job.title).strip().replace(' ', '-').lower()
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        
        filename = f"{company_name}-{position_name}-{timestamp}.docx"
        filepath = os.path.join(self.output_dir, filename)
        
        # Create Word document
        doc = Document()
        
        # Format document
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(11)
        
        # Add cover letter content
        for paragraph in cover_letter.split('\n'):
            p = doc.add_paragraph(paragraph)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Save document
        doc.save(filepath)
        
        logger.info(f"Saved cover letter to {filepath}")
        
        return filepath


if __name__ == "__main__":
    # Test the cover letter generator
    import json
    from automation.job_search import JobPost
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Sample resume data
    sample_resume = {
        'contact_info': {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '(555) 123-4567',
            'location': 'San Francisco, CA'
        },
        'skills': [
            'Python', 'JavaScript', 'React', 'Node.js', 'Django', 
            'SQL', 'AWS', 'Docker', 'Kubernetes', 'Git'
        ],
        'experience': [
            {
                'position': 'Senior Software Engineer',
                'company': 'Tech Company A',
                'start_date': 'Jan 2020',
                'end_date': 'Present',
                'description': 'Led development of cloud-based applications.'
            },
            {
                'position': 'Software Engineer',
                'company': 'Tech Company B',
                'start_date': 'Mar 2017',
                'end_date': 'Dec 2019',
                'description': 'Developed web applications using React and Node.js.'
            }
        ]
    }
    
    # Sample job
    sample_job = JobPost(
        title="Senior Software Developer",
        company="Example Corp",
        location="Remote",
        description="We're looking for a Senior Software Developer with experience in Python and React...",
        url="https://example.com/jobs/123",
        job_board="Example",
        date_posted="2025-04-01",
        job_type="Full-time"
    )
    
    # Sample match data
    sample_match_data = {
        'overall_score': 85.5,
        'matching_skills': ['Python', 'React', 'JavaScript'],
        'missing_skills': ['GraphQL', 'TypeScript'],
        'job_skills': ['Python', 'React', 'JavaScript', 'GraphQL', 'TypeScript'],
        'strengths': [
            'Has experience with Python',
            'Has experience with React',
            'Has 5.0 years of relevant experience'
        ]
    }
    
    # Initialize generator
    generator = CoverLetterGenerator(sample_resume)
    
    # Generate cover letter
    cover_letter = generator.generate_cover_letter(sample_job, sample_match_data)
    
    # Print cover letter
    print("\nGenerated Cover Letter:")
    print("=" * 50)
    print(cover_letter)
    print("=" * 50)
    
    # Save cover letter
    txt_path = generator.save_cover_letter_txt(cover_letter, sample_job)
    docx_path = generator.save_cover_letter_docx(cover_letter, sample_job)
    
    print(f"\nSaved as text: {txt_path}")
    print(f"Saved as Word document: {docx_path}")
