#!/usr/bin/env python3

"""
Resume-Job Matcher

This module matches resumes to job descriptions using NLP techniques
to calculate relevance scores and identify strengths/weaknesses.
"""

import re
import logging
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import spacy
from spacy.tokens import Doc

from .parser import ResumeParser

logger = logging.getLogger(__name__)

# Load spaCy model (will be loaded by parser module)
nlp = spacy.load("en_core_web_md")

class JobMatcher:
    """Match resumes to job descriptions and calculate relevance scores"""
    
    def __init__(self, resume_parser: ResumeParser):
        """
        Initialize the job matcher with a parsed resume.
        
        Args:
            resume_parser: A ResumeParser instance with a parsed resume
        """
        self.resume_parser = resume_parser
        self.resume_data = resume_parser.get_parsed_data()
        self.resume_nlp = nlp(self.resume_data['raw_text'])
        
        # Extract key vectors from resume
        self.resume_skills_vec = self._get_skills_vector(self.resume_data['skills'])
        
    def match_job(self, job_description: str) -> Dict[str, Any]:
        """
        Match the resume to a job description and calculate relevance scores.
        
        Args:
            job_description: The job description text
            
        Returns:
            Dictionary with match scores and analysis
        """
        # Process the job description
        job_doc = nlp(job_description)
        
        # Extract skills from job description
        job_skills = self._extract_skills_from_job(job_description)
        job_skills_vec = self._get_skills_vector(job_skills)
        
        # Calculate various scores
        skill_match_score = self._calculate_skill_match(job_skills)
        experience_match_score = self._calculate_experience_match(job_description)
        education_match_score = self._calculate_education_match(job_description)
        semantic_match_score = self._calculate_semantic_match(job_doc)
        
        # Identify matching and missing skills
        matching_skills = [skill for skill in self.resume_data['skills'] if skill in job_skills]
        missing_skills = [skill for skill in job_skills if skill not in self.resume_data['skills']]
        
        # Calculate overall match score (weighted average of individual scores)
        weights = {
            'skill_match': 0.40,
            'experience_match': 0.30,
            'education_match': 0.15,
            'semantic_match': 0.15
        }
        
        overall_score = (
            skill_match_score * weights['skill_match'] +
            experience_match_score * weights['experience_match'] +
            education_match_score * weights['education_match'] +
            semantic_match_score * weights['semantic_match']
        ) * 100  # Convert to percentage
        
        # Prepare the match results
        match_result = {
            'overall_score': round(overall_score, 1),
            'skill_match_score': round(skill_match_score * 100, 1),
            'experience_match_score': round(experience_match_score * 100, 1),
            'education_match_score': round(education_match_score * 100, 1),
            'semantic_match_score': round(semantic_match_score * 100, 1),
            'matching_skills': matching_skills,
            'missing_skills': missing_skills,
            'job_skills': job_skills,
            'strengths': self._identify_strengths(job_doc),
            'weaknesses': self._identify_weaknesses(job_doc, matching_skills, missing_skills),
            'keywords': self._extract_important_keywords(job_doc)
        }
        
        return match_result
    
    def _extract_skills_from_job(self, job_text: str) -> List[str]:
        """Extract skills from job description text"""
        # This is a simplified implementation
        # In practice, you'd want to use more sophisticated techniques
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
        job_text_lower = job_text.lower()
        
        for skill in common_skills:
            # Check for whole word match
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, job_text_lower):
                found_skills.append(skill)
        
        return found_skills
    
    def _get_skills_vector(self, skills: List[str]) -> np.ndarray:
        """Convert a list of skills to a vector representation"""
        if not skills:
            return np.zeros(300)  # Default spaCy vector dimension
        
        # Get vector representation of each skill and average them
        vectors = [nlp(skill).vector for skill in skills]
        return np.mean(vectors, axis=0)
    
    def _calculate_skill_match(self, job_skills: List[str]) -> float:
        """
        Calculate skill match score based on matching skills
        
        Returns:
            float: Score between 0 and 1
        """
        if not job_skills:
            return 0.0
        
        resume_skills = set(self.resume_data['skills'])
        job_skills_set = set(job_skills)
        
        # Number of matching skills
        matching_skills = resume_skills.intersection(job_skills_set)
        
        # Calculate Jaccard similarity
        if not resume_skills and not job_skills_set:
            return 0.0
        
        return len(matching_skills) / len(job_skills_set)
    
    def _calculate_experience_match(self, job_description: str) -> float:
        """
        Calculate experience match score based on years of experience
        
        Returns:
            float: Score between 0 and 1
        """
        # Extract required years of experience from job description
        year_patterns = [
            r'(\d+)\+?\s*(?:years|yrs|yr)(?:\s*of)?\s*(?:experience|work)',
            r'(?:experience|work)(?:\s*of)?\s*(\d+)\+?\s*(?:years|yrs|yr)',
            r'minimum\s*(?:of)?\s*(\d+)\+?\s*(?:years|yrs|yr)',
            r'at\s*least\s*(\d+)\+?\s*(?:years|yrs|yr)'
        ]
        
        required_years = 0
        for pattern in year_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE)
            if matches:
                required_years = int(matches[0])
                break
        
        # Default to 3 years if not specified
        if required_years == 0:
            required_years = 3
        
        # Get candidate's years of experience
        candidate_years = self.resume_parser.get_experience_years()
        
        # Calculate score (max out at 1.5x the required experience)
        if candidate_years >= required_years * 1.5:
            return 1.0
        elif candidate_years >= required_years:
            # Scale between 0.8 and 1.0
            return 0.8 + 0.2 * (candidate_years - required_years) / (required_years * 0.5)
        else:
            # Scale between 0 and 0.8
            return min(0.8, candidate_years / required_years)
    
    def _calculate_education_match(self, job_description: str) -> float:
        """
        Calculate education match score
        
        Returns:
            float: Score between 0 and 1
        """
        # Extract required education level from job description
        education_levels = {
            "phd": 4,
            "doctorate": 4,
            "ph.d": 4,
            "master": 3,
            "ms": 3,
            "m.s.": 3,
            "m.a.": 3,
            "mba": 3,
            "m.b.a.": 3,
            "bachelor": 2,
            "bs": 2,
            "b.s.": 2,
            "ba": 2,
            "b.a.": 2,
            "associate": 1,
            "a.a.": 1,
            "a.s.": 1
        }
        
        # Determine required education level
        required_level = 0
        for level, value in education_levels.items():
            if re.search(r'\b' + re.escape(level) + r'\b', job_description, re.IGNORECASE):
                required_level = max(required_level, value)
        
        # Default to bachelor's if not specified
        if required_level == 0:
            required_level = 2
        
        # Determine candidate's education level
        candidate_level = 0
        for edu in self.resume_data['education']:
            degree = edu.get('degree', '').lower()
            for level, value in education_levels.items():
                if level in degree:
                    candidate_level = max(candidate_level, value)
        
        # Calculate score
        if candidate_level >= required_level:
            return 1.0
        elif candidate_level == required_level - 1:
            return 0.7  # One level below
        elif candidate_level > 0:
            return 0.4  # More than one level below but has some education
        else:
            return 0.0  # No education
    
    def _calculate_semantic_match(self, job_doc: Doc) -> float:
        """
        Calculate semantic similarity between resume and job description
        
        Returns:
            float: Score between 0 and 1
        """
        # Calculate cosine similarity between resume and job description vectors
        if not job_doc.vector.any() or not self.resume_nlp.vector.any():
            return 0.5  # Default if vectors are zero
        
        cosine_sim = job_doc.similarity(self.resume_nlp)
        
        # Normalize to 0-1 range (sometimes spaCy similarity can be slightly outside this range)
        return max(0.0, min(1.0, cosine_sim))
    
    def _identify_strengths(self, job_doc: Doc) -> List[str]:
        """Identify strengths based on matching skills and experience"""
        strengths = []
        
        # Add matching skills as strengths
        for skill in self.resume_data['skills']:
            if skill in job_doc.text.lower():
                strengths.append(f"Has experience with {skill}")
        
        # Add experience strength if applicable
        experience_years = self.resume_parser.get_experience_years()
        if experience_years >= 5:
            strengths.append(f"Has {experience_years:.1f} years of relevant experience")
        
        # Add education strength if applicable
        education = self.resume_data['education']
        if education:
            degrees = [edu.get('degree', '') for edu in education]
            if any('master' in degree.lower() or 'm.s.' in degree.lower() for degree in degrees):
                strengths.append("Has a Master's degree")
            elif any('bachelor' in degree.lower() or 'b.s.' in degree.lower() for degree in degrees):
                strengths.append("Has a Bachelor's degree")
        
        return strengths
    
    def _identify_weaknesses(self, job_doc: Doc, matching_skills: List[str], missing_skills: List[str]) -> List[str]:
        """Identify weaknesses based on missing skills and experience"""
        weaknesses = []
        
        # Add missing skills as weaknesses
        if len(missing_skills) > 0:
            if len(missing_skills) <= 3:
                for skill in missing_skills:
                    weaknesses.append(f"Missing experience with {skill}")
            else:
                weaknesses.append(f"Missing {len(missing_skills)} required skills")
        
        # Add experience weakness if applicable
        experience_years = self.resume_parser.get_experience_years()
        year_pattern = r'(\d+)\+?\s*(?:years|yrs|yr)(?:\s*of)?\s*(?:experience|work)'
        matches = re.findall(year_pattern, job_doc.text, re.IGNORECASE)
        
        if matches and experience_years < int(matches[0]):
            weaknesses.append(f"Has {experience_years:.1f} years of experience but job requires {matches[0]}")
        
        return weaknesses
    
    def _extract_important_keywords(self, job_doc: Doc) -> List[str]:
        """Extract important keywords from job description for cover letter generation"""
        keywords = []
        
        # Extract named entities
        for ent in job_doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'WORK_OF_ART']:
                keywords.append(ent.text)
        
        # Extract noun phrases
        for chunk in job_doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Limit to phrases with 3 or fewer words
                keywords.append(chunk.text)
        
        # Deduplicate and limit to 10 keywords
        unique_keywords = list(set(keywords))
        return unique_keywords[:10]


def generate_cover_letter(resume_data: Dict[str, Any], job_data: Dict[str, Any], 
                         match_result: Dict[str, Any]) -> str:
    """
    Generate a cover letter based on resume and job match
    
    Args:
        resume_data: Parsed resume data
        job_data: Job posting data
        match_result: Result from matching resume to job
        
    Returns:
        str: Generated cover letter text
    """
    # This is a simplified implementation
    # In a real implementation, you would use a LLM or template system
    
    # Basic template
    template = f"""
{resume_data['contact_info'].get('name', 'Your Name')}
{resume_data['contact_info'].get('email', 'your.email@example.com')}
{resume_data['contact_info'].get('phone', '(123) 456-7890')}
{resume_data['contact_info'].get('location', 'Your City, State')}

{job_data.get('date', 'Current Date')}

{job_data.get('company_name', 'Company Name')}
{job_data.get('company_address', 'Company Address')}

Dear Hiring Manager,

I am writing to express my interest in the {job_data.get('title', 'position')} role at {job_data.get('company_name', 'your company')}. With {resume_data.get('experience_years', 'several')} years of experience in the field, I believe my skills and background make me a strong candidate for this position.

{resume_data.get('summary', 'Professional summary would appear here.')}

I have extensive experience with {', '.join(match_result['matching_skills'][:5])} which align perfectly with the requirements in your job posting. Throughout my career, I have:
- Developed expertise in various relevant technologies and methodologies
- Collaborated effectively with cross-functional teams
- Delivered high-quality solutions that met business objectives

I am particularly drawn to {job_data.get('company_name', 'your company')} because of your commitment to innovation and excellence in the field. I am confident that my experience and passion for {job_data.get('industry', 'the industry')} would make me a valuable addition to your team.

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and experience can contribute to {job_data.get('company_name', 'your company')}'s continued success.

Sincerely,
{resume_data['contact_info'].get('name', 'Your Name')}
    """
    
    return template.strip()


if __name__ == "__main__":
    # Simple test code
    from .parser import ResumeParser, get_resume_files
    
    resume_files = get_resume_files()
    
    if not resume_files:
        print("No resume files found in resume/data/ directory.")
        print("Please add your resume file (PDF, DOCX, or TXT format) to the resume/data/ directory.")
    else:
        print(f"Testing with resume: {resume_files[0].name}")
        
        try:
            # Parse resume
            parser = ResumeParser(resume_files[0])
            
            # Create matcher
            matcher = JobMatcher(parser)
            
            # Test with a sample job description
            sample_job = """
            Senior Software Engineer

            Requirements:
            - 5+ years of experience in software development
            - Proficiency in Python, JavaScript, and React
            - Experience with AWS and cloud technologies
            - Bachelor's degree in Computer Science or related field
            - Strong communication and teamwork skills
            
            Responsibilities:
            - Design and implement new features for our web application
            - Collaborate with product and design teams
            - Mentor junior developers
            - Participate in code reviews and agile development process
            """
            
            match_result = matcher.match_job(sample_job)
            
            print(f"Overall match score: {match_result['overall_score']}%")
            print(f"Skill match score: {match_result['skill_match_score']}%")
            print(f"Experience match score: {match_result['experience_match_score']}%")
            print(f"Education match score: {match_result['education_match_score']}%")
            print(f"Semantic match score: {match_result['semantic_match_score']}%")
            
            print("\nMatching skills:")
            for skill in match_result['matching_skills']:
                print(f" - {skill}")
            
            print("\nMissing skills:")
            for skill in match_result['missing_skills']:
                print(f" - {skill}")
            
            print("\nStrengths:")
            for strength in match_result['strengths']:
                print(f" - {strength}")
            
            print("\nWeaknesses:")
            for weakness in match_result['weaknesses']:
                print(f" - {weakness}")
            
            # Generate a cover letter
            job_data = {
                'title': 'Senior Software Engineer',
                'company_name': 'Example Corp',
                'date': 'April 9, 2025',
                'industry': 'software development'
            }
            
            cover_letter = generate_cover_letter(parser.get_parsed_data(), job_data, match_result)
            print("\nGenerated Cover Letter:")
            print("-" * 50)
            print(cover_letter)
            
        except Exception as e:
            print(f"Error during matching: {e}")
