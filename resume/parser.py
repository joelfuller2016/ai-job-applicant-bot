#!/usr/bin/env python3

"""
Resume Parser

This module is responsible for parsing resumes in various formats (PDF, DOCX, TXT)
and extracting relevant information such as skills, experience, education, etc.
"""

import os
import re
import logging
import spacy
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Document processing
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document

logger = logging.getLogger(__name__)

# Load spaCy model for NLP tasks
try:
    nlp = spacy.load("en_core_web_md")
    logger.info("Loaded spaCy model en_core_web_md")
except OSError:
    logger.warning("SpaCy model not found. Downloading en_core_web_md...")
    os.system("python -m spacy download en_core_web_md")
    nlp = spacy.load("en_core_web_md")
    logger.info("Downloaded and loaded spaCy model en_core_web_md")

class ResumeParser:
    """Parser for resume documents in various formats"""
    
    def __init__(self, resume_path: Union[str, Path]):
        """
        Initialize the resume parser with the path to the resume file.
        
        Args:
            resume_path: Path to the resume file (PDF, DOCX, or TXT)
        """
        self.resume_path = Path(resume_path)
        self.text = None
        self.parsed_data = {}
        
        if not self.resume_path.exists():
            raise FileNotFoundError(f"Resume file not found: {self.resume_path}")

        # Parse the resume
        self.text = self._extract_text()
        if not self.text:
            raise ValueError(f"Could not extract text from resume: {self.resume_path}")
        
        # Parse the resume data
        self.parsed_data = self._parse_resume()
        
    def _extract_text(self) -> str:
        """
        Extract text from the resume file based on its format.
        
        Returns:
            str: Extracted text from the resume
        """
        file_extension = self.resume_path.suffix.lower()
        
        try:
            if file_extension == '.pdf':
                return extract_pdf_text(self.resume_path)
            elif file_extension == '.docx':
                doc = Document(self.resume_path)
                return ' '.join([para.text for para in doc.paragraphs])
            elif file_extension == '.txt':
                with open(self.resume_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.error(f"Unsupported file format: {file_extension}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from resume: {e}")
            return ""
    
    def _parse_resume(self) -> Dict[str, Any]:
        """
        Parse the resume text to extract structured information.
        
        Returns:
            dict: Parsed resume data including contact info, skills, experience, etc.
        """
        doc = nlp(self.text)
        
        # Initialize the structured data
        parsed_data = {
            'contact_info': self._extract_contact_info(doc),
            'skills': self._extract_skills(doc),
            'experience': self._extract_experience(doc),
            'education': self._extract_education(doc),
            'summary': self._extract_summary(doc),
            'raw_text': self.text
        }
        
        return parsed_data
    
    def _extract_contact_info(self, doc) -> Dict[str, str]:
        """Extract contact information from the resume"""
        # This is a simplified implementation
        contact_info = {
            'name': '',
            'email': '',
            'phone': '',
            'location': '',
            'linkedin': '',
            'github': ''
        }
        
        # Extract email using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, self.text)
        if emails:
            contact_info['email'] = emails[0]
        
        # Extract phone using regex
        phone_pattern = r'(\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'
        phones = re.findall(phone_pattern, self.text)
        if phones:
            contact_info['phone'] = phones[0]
        
        # Extract LinkedIn profile
        linkedin_pattern = r'linkedin\.com/in/[a-zA-Z0-9_-]+'
        linkedin = re.findall(linkedin_pattern, self.text.lower())
        if linkedin:
            contact_info['linkedin'] = f"https://www.{linkedin[0]}"
        
        # Extract GitHub profile
        github_pattern = r'github\.com/[a-zA-Z0-9_-]+'
        github = re.findall(github_pattern, self.text.lower())
        if github:
            contact_info['github'] = f"https://www.{github[0]}"
        
        # Name extraction is more complex and would need more sophisticated logic
        # This is a simplified approach
        for ent in doc.ents:
            if ent.label_ == "PERSON" and not contact_info['name']:
                contact_info['name'] = ent.text
        
        return contact_info
    
    def _extract_skills(self, doc) -> List[str]:
        """Extract skills from the resume"""
        # This would need a comprehensive skills database or ML model in practice
        common_skills = [
            "python", "javascript", "typescript", "java", "c++", "c#", "react",
            "angular", "vue", "node.js", "express", "django", "flask", "fastapi",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "git",
            "jenkins", "circleci", "github actions", "jira", "confluence", "agile",
            "scrum", "kanban", "sql", "nosql", "mongodb", "postgresql", "mysql",
            "oracle", "redis", "kafka", "rabbitmq", "machine learning", "ai", 
            "deep learning", "data science", "data analysis", "tableau", "power bi",
            "excel", "product management", "project management"
        ]
        
        # Find skills using simple keyword matching
        found_skills = []
        text_lower = self.text.lower()
        
        for skill in common_skills:
            # Check for whole word match
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        
        return found_skills
    
    def _extract_experience(self, doc) -> List[Dict[str, str]]:
        """Extract work experience from the resume"""
        # This is a simplified placeholder implementation
        # In a real implementation, this would use more sophisticated techniques
        experiences = []
        
        # Simple regex to find date ranges like "2018 - 2020" or "Jan 2018 - Dec 2020"
        date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*\d{4})\s*[-–—]\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*\d{4}|Present|Current)'
        
        experience_sections = self._extract_sections(self.text, ["experience", "work history", "employment"])
        
        if experience_sections:
            date_matches = re.findall(date_pattern, experience_sections)
            
            for i, match in enumerate(date_matches):
                start_date, end_date = match
                
                # Extract position and company (simplified)
                # In practice, this would need more sophisticated parsing
                experiences.append({
                    'position': f"Position {i+1}",  # Placeholder
                    'company': f"Company {i+1}",    # Placeholder
                    'start_date': start_date.strip(),
                    'end_date': end_date.strip(),
                    'description': "Experience details would be extracted here"  # Placeholder
                })
        
        return experiences
    
    def _extract_education(self, doc) -> List[Dict[str, str]]:
        """Extract education information from the resume"""
        # Simplified implementation
        education = []
        
        education_section = self._extract_sections(self.text, ["education", "academic background"])
        
        if education_section:
            # Extract degrees using regex
            degree_pattern = r'(Bachelor|Master|PhD|Doctorate|B\.S\.|M\.S\.|B\.A\.|M\.A\.|M\.B\.A\.|Ph\.D\.)'
            degrees = re.findall(degree_pattern, education_section)
            
            for i, degree in enumerate(degrees):
                education.append({
                    'degree': degree,
                    'institution': f"University {i+1}",  # Placeholder
                    'graduation_date': "",  # Would extract dates in real implementation
                    'major': ""  # Would extract major in real implementation
                })
        
        return education
    
    def _extract_summary(self, doc) -> str:
        """Extract professional summary from the resume"""
        # Look for a summary section
        summary_section = self._extract_sections(self.text, ["summary", "professional summary", "profile", "objective"])
        
        if summary_section:
            # Extract the first paragraph of the summary section
            paragraphs = summary_section.split('\n\n')
            if paragraphs:
                return paragraphs[0]
        
        # If no summary section found, return the first 250 characters as a fallback
        return self.text[:250] if self.text else ""
    
    def _extract_sections(self, text: str, section_headers: List[str]) -> str:
        """Helper method to extract content from specific sections in the resume"""
        text_lower = text.lower()
        
        # Try to find the specified section
        for header in section_headers:
            pattern = r'(?i)\b' + re.escape(header) + r'\b.*?(?=\n\s*\n\s*\b(?:' + '|'.join([re.escape(h) for h in section_headers + ["skills", "experience", "education", "projects", "references"]]) + r')\b|\Z)'
            
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                return matches[0]
        
        return ""
    
    def get_parsed_data(self) -> Dict[str, Any]:
        """Get the parsed resume data"""
        return self.parsed_data
    
    def get_skills(self) -> List[str]:
        """Get the list of skills extracted from the resume"""
        return self.parsed_data.get('skills', [])
    
    def get_experience_years(self) -> float:
        """
        Calculate approximate years of experience based on work history
        
        Returns:
            float: Approximate years of experience
        """
        total_years = 0.0
        experiences = self.parsed_data.get('experience', [])
        
        for exp in experiences:
            start = exp.get('start_date', '')
            end = exp.get('end_date', '')
            
            # Extract years
            start_year = self._extract_year(start)
            end_year = self._extract_year(end) if end.lower() not in ['present', 'current'] else 2025
            
            if start_year and end_year:
                total_years += end_year - start_year
        
        return total_years
    
    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract the year from a date string"""
        year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if year_match:
            return int(year_match.group(0))
        return None


def get_resume_files(resume_dir: Union[str, Path] = 'resume/data') -> List[Path]:
    """
    Get a list of resume files in the specified directory.
    
    Args:
        resume_dir: Directory containing resume files
        
    Returns:
        List of Path objects for resume files
    """
    resume_dir = Path(resume_dir)
    if not resume_dir.exists():
        logger.warning(f"Resume directory not found: {resume_dir}")
        return []
    
    # Look for PDF, DOCX, and TXT files
    resume_files = []
    for ext in ['.pdf', '.docx', '.txt']:
        resume_files.extend(resume_dir.glob(f'*{ext}'))
    
    return resume_files


if __name__ == "__main__":
    # Simple test code
    resume_files = get_resume_files()
    
    if not resume_files:
        print("No resume files found in resume/data/ directory.")
        print("Please add your resume file (PDF, DOCX, or TXT format) to the resume/data/ directory.")
    else:
        print(f"Found {len(resume_files)} resume file(s):")
        for resume_file in resume_files:
            print(f" - {resume_file.name}")
            
            try:
                parser = ResumeParser(resume_file)
                data = parser.get_parsed_data()
                
                print(f"Extracted {len(data['skills'])} skills:")
                print(", ".join(data['skills'][:10]) + ("..." if len(data['skills']) > 10 else ""))
                
                print(f"Extracted {len(data['experience'])} work experiences")
                print(f"Extracted {len(data['education'])} education entries")
                print(f"Approximate years of experience: {parser.get_experience_years():.1f}")
            except Exception as e:
                print(f"Error parsing resume: {e}")
