#!/usr/bin/env python3

"""
Job Analyzer

Analyzes job descriptions using AI to determine match with resume and extract key information.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Import utilities
from utils.advanced_logging import get_logger
from utils.helpers import normalize_string, extract_keywords, merge_dicts

# Load environment variables
load_dotenv()

# Configure logger
logger = get_logger("job_analyzer")

class JobAnalyzer:
    """
    Analyzes job descriptions using AI to determine match with resume and extract key information.
    Uses LLMs to understand both explicit and implicit requirements in the job description.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the job analyzer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.ai_config = config.get('ai', {})
        
        # Match threshold (0-100)
        self.match_threshold = self.ai_config.get('match_threshold', 70)
        
        # LLM configuration
        self.llm_model = self.ai_config.get('llm_model', 'gpt-4-turbo')
        self.temperature = self.ai_config.get('temperature', 0.2)
        self.max_tokens = self.ai_config.get('max_tokens', 4096)
        
        # LLM instance
        self.llm = None
    
    async def initialize(self):
        """Initialize the job analyzer"""
        try:
            # Initialize LLM based on configuration
            if self.llm_model.startswith("gpt-"):
                # OpenAI model
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=self.llm_model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                logger.info(f"Initialized OpenAI LLM: {self.llm_model}")
            
            elif self.llm_model.startswith("claude-"):
                # Anthropic model
                from langchain_anthropic import ChatAnthropic
                self.llm = ChatAnthropic(
                    model=self.llm_model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                logger.info(f"Initialized Anthropic LLM: {self.llm_model}")
            
            else:
                # Default to OpenAI as fallback
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model='gpt-4-turbo',
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                logger.info(f"Initialized default OpenAI LLM: gpt-4-turbo")
            
            return self
        
        except Exception as e:
            logger.error(f"Error initializing job analyzer: {e}")
            raise
    
    async def analyze_job(self, job_description: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a job description and determine match with resume
        
        Args:
            job_description: Job description text
            resume_data: Resume data as a dictionary
            
        Returns:
            Analysis results
        """
        try:
            logger.info("Analyzing job description...")
            
            # Extract features from job description
            job_features = await self._extract_job_features(job_description)
            
            # Extract features from resume
            resume_features = self._extract_resume_features(resume_data)
            
            # Calculate match score (through AI)
            match_results = await self._calculate_match_score(job_features, resume_features)
            
            # Generate talking points for cover letter
            cover_letter_points = await self._generate_cover_letter_points(job_features, resume_features, match_results)
            
            # Combine all results
            analysis = {
                "match_score": match_results.get("match_score", 0),
                "matching_skills": match_results.get("matching_skills", []),
                "missing_skills": match_results.get("missing_skills", []),
                "job_features": job_features,
                "assessment": match_results.get("assessment", ""),
                "cover_letter_points": cover_letter_points
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing job: {e}")
            # Return minimal analysis with zero match score
            return {
                "match_score": 0,
                "matching_skills": [],
                "missing_skills": [],
                "assessment": f"Error analyzing job: {str(e)}",
                "cover_letter_points": []
            }
    
    async def _extract_job_features(self, job_description: str) -> Dict[str, Any]:
        """
        Extract key features from a job description using AI
        
        Args:
            job_description: Job description text
            
        Returns:
            Dictionary of job features
        """
        try:
            from langchain.prompts import ChatPromptTemplate
            
            # Prompt template
            prompt = ChatPromptTemplate.from_template("""
            You are an expert job analyzer that extracts key information from job descriptions.
            Analyze the following job description and extract key details in a structured format.
            
            JOB DESCRIPTION:
            {job_description}
            
            Please extract the following information:
            1. Job Title: The exact job title or role
            2. Required Skills: Technical and soft skills explicitly required for the role
            3. Preferred Skills: Skills that are preferred but not required
            4. Experience: Required years of experience or specific experience needed
            5. Education: Required educational qualifications
            6. Responsibilities: Key job responsibilities and duties
            7. Company Values: Any mentioned company values or culture
            8. Job Type: Full-time, part-time, contract, etc.
            9. Seniority Level: Junior, mid-level, senior, etc.
            10. Industry: The industry or sector
            
            Return the information in a JSON format with the following keys:
            job_title, required_skills, preferred_skills, experience, education, responsibilities,
            company_values, job_type, seniority_level, industry.
            
            For lists (like skills), return an array of strings. If information is not available,
            use null for that field.
            """)
            
            # Generate response
            chain = prompt | self.llm
            response = await chain.ainvoke({"job_description": job_description})
            
            # Parse JSON response
            try:
                # Extract text content from response
                if hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = str(response)
                    
                # Clean up response to ensure valid JSON
                # Sometimes the LLM might include extra text before or after the JSON
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    features = json.loads(json_text)
                else:
                    logger.warning("Couldn't extract valid JSON from response")
                    features = {}
                    
                return features
                
            except json.JSONDecodeError:
                logger.error("Error parsing JSON from job features response")
                # Return empty features if parsing fails
                return {}
                
        except Exception as e:
            logger.error(f"Error extracting job features: {e}")
            return {}
    
    def _extract_resume_features(self, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key features from resume data
        
        Args:
            resume_data: Resume data as a dictionary
            
        Returns:
            Dictionary of resume features
        """
        features = {}
        
        try:
            # Extract basic info
            basic_info = resume_data.get('basic_info', {})
            features['name'] = basic_info.get('name', '')
            
            # Extract skills
            skills = resume_data.get('skills', [])
            if isinstance(skills, list):
                features['skills'] = skills
            elif isinstance(skills, dict):
                # Handle case where skills are categorized
                all_skills = []
                for skill_category, skill_list in skills.items():
                    if isinstance(skill_list, list):
                        all_skills.extend(skill_list)
                    elif skill_category == 'technical' or skill_category == 'soft':
                        # Special handling for technical/soft skills
                        if isinstance(skill_list, list):
                            all_skills.extend(skill_list)
                features['skills'] = all_skills
            else:
                features['skills'] = []
            
            # Extract experience
            experience = resume_data.get('experience', [])
            features['experience'] = []
            
            for job in experience:
                job_info = {
                    'title': job.get('title', ''),
                    'company': job.get('company', ''),
                    'description': job.get('description', ''),
                    'duration': self._calculate_job_duration(job)
                }
                
                # Extract achievements
                if 'achievements' in job and isinstance(job['achievements'], list):
                    job_info['achievements'] = job['achievements']
                
                # Extract technologies
                if 'technologies' in job and isinstance(job['technologies'], list):
                    job_info['technologies'] = job['technologies']
                
                features['experience'].append(job_info)
            
            # Calculate total experience
            features['total_experience_years'] = self._calculate_total_experience(experience)
            
            # Extract education
            education = resume_data.get('education', [])
            features['education'] = education
            
            # Extract highest education level
            features['highest_education'] = self._get_highest_education(education)
            
            # Extract projects
            projects = resume_data.get('projects', [])
            features['projects'] = projects
            
            # Extract preferences
            preferences = resume_data.get('preferences', {})
            features['preferences'] = preferences
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting resume features: {e}")
            return {}
    
    def _calculate_job_duration(self, job: Dict[str, Any]) -> Optional[float]:
        """
        Calculate job duration in years
        
        Args:
            job: Job dictionary from resume
            
        Returns:
            Duration in years, or None if can't be calculated
        """
        try:
            from datetime import datetime
            
            # Get start and end dates
            start_date = job.get('start_date')
            end_date = job.get('end_date', 'Present')
            
            if not start_date:
                return None
            
            # Parse dates
            if '-' in start_date:
                # Format: YYYY-MM
                start_date = datetime.strptime(start_date, '%Y-%m')
            else:
                # Try other formats
                try:
                    start_date = datetime.strptime(start_date, '%Y/%m')
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_date, '%m/%Y')
                    except ValueError:
                        return None
            
            if end_date == 'Present':
                end_date = datetime.now()
            else:
                try:
                    if '-' in end_date:
                        # Format: YYYY-MM
                        end_date = datetime.strptime(end_date, '%Y-%m')
                    else:
                        # Try other formats
                        try:
                            end_date = datetime.strptime(end_date, '%Y/%m')
                        except ValueError:
                            try:
                                end_date = datetime.strptime(end_date, '%m/%Y')
                            except ValueError:
                                return None
                except ValueError:
                    return None
            
            # Calculate duration in years
            duration = (end_date.year - start_date.year) + (end_date.month - start_date.month) / 12
            return max(0, duration)  # Ensure non-negative
            
        except Exception as e:
            logger.error(f"Error calculating job duration: {e}")
            return None
    
    def _calculate_total_experience(self, experience: List[Dict[str, Any]]) -> float:
        """
        Calculate total years of experience
        
        Args:
            experience: List of experience dictionaries
            
        Returns:
            Total years of experience
        """
        total_years = 0.0
        
        for job in experience:
            duration = self._calculate_job_duration(job)
            if duration is not None:
                total_years += duration
        
        return total_years
    
    def _get_highest_education(self, education: List[Dict[str, Any]]) -> Optional[str]:
        """
        Get highest education level
        
        Args:
            education: List of education dictionaries
            
        Returns:
            Highest education level, or None if can't be determined
        """
        education_ranks = {
            'phd': 5,
            'ph.d': 5,
            'doctorate': 5,
            'doctoral': 5,
            'master': 4,
            'ms': 4,
            'ma': 4,
            'mba': 4,
            'm.s': 4,
            'm.a': 4,
            'bachelor': 3,
            'bs': 3,
            'ba': 3,
            'b.s': 3,
            'b.a': 3,
            'associate': 2,
            'as': 2,
            'aa': 2,
            'a.s': 2,
            'a.a': 2,
            'certificate': 1,
            'certification': 1,
            'diploma': 1,
            'high school': 0,
            'ged': 0
        }
        
        highest_rank = -1
        highest_education = None
        
        for edu in education:
            degree = edu.get('degree', '').lower()
            
            for key, rank in education_ranks.items():
                if key in degree and rank > highest_rank:
                    highest_rank = rank
                    highest_education = edu.get('degree')
        
        return highest_education
    
    async def _calculate_match_score(self, job_features: Dict[str, Any], resume_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate match score between job and resume using AI
        
        Args:
            job_features: Job features
            resume_features: Resume features
            
        Returns:
            Match results
        """
        try:
            from langchain.prompts import ChatPromptTemplate
            
            # Prepare prompt template
            prompt = ChatPromptTemplate.from_template("""
            You are an expert job match analyzer. Evaluate how well a candidate's profile matches a job description.
            
            JOB FEATURES:
            {job_features}
            
            CANDIDATE FEATURES:
            {resume_features}
            
            Please provide:
            1. Match Score (0-100): A numerical score indicating how well the candidate matches the job requirements
            2. Matching Skills: A list of skills from the candidate that match the job requirements
            3. Missing Skills: A list of skills required by the job that the candidate doesn't have
            4. Assessment: A brief assessment of how well the candidate matches the job (2-3 sentences)
            
            Return the results as a JSON object with the following keys:
            match_score, matching_skills, missing_skills, assessment.
            
            For the match_score, consider both required and preferred skills, experience, education, and other factors.
            For the matching_skills and missing_skills, focus on technical and soft skills.
            For the assessment, highlight the key strengths and weaknesses of the candidate for this role.
            """)
            
            # Convert features to strings for the prompt
            job_features_str = json.dumps(job_features, indent=2)
            resume_features_str = json.dumps(resume_features, indent=2)
            
            # Generate response
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "job_features": job_features_str,
                "resume_features": resume_features_str
            })
            
            # Parse JSON response
            try:
                # Extract text content from response
                if hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = str(response)
                    
                # Clean up response to ensure valid JSON
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    match_results = json.loads(json_text)
                    
                    # Ensure match_score is a number
                    if 'match_score' in match_results:
                        try:
                            match_results['match_score'] = float(match_results['match_score'])
                        except (ValueError, TypeError):
                            match_results['match_score'] = 0
                    else:
                        match_results['match_score'] = 0
                        
                    return match_results
                else:
                    logger.warning("Couldn't extract valid JSON from match score response")
                    return {
                        "match_score": 0,
                        "matching_skills": [],
                        "missing_skills": [],
                        "assessment": "Error calculating match score."
                    }
                    
            except json.JSONDecodeError:
                logger.error("Error parsing JSON from match score response")
                return {
                    "match_score": 0,
                    "matching_skills": [],
                    "missing_skills": [],
                    "assessment": "Error calculating match score."
                }
                
        except Exception as e:
            logger.error(f"Error calculating match score: {e}")
            return {
                "match_score": 0,
                "matching_skills": [],
                "missing_skills": [],
                "assessment": f"Error calculating match score: {str(e)}"
            }
    
    async def _generate_cover_letter_points(self, job_features: Dict[str, Any], resume_features: Dict[str, Any], match_results: Dict[str, Any]) -> List[str]:
        """
        Generate talking points for a cover letter
        
        Args:
            job_features: Job features
            resume_features: Resume features
            match_results: Match results
            
        Returns:
            List of talking points
        """
        try:
            from langchain.prompts import ChatPromptTemplate
            
            # Prepare prompt template
            prompt = ChatPromptTemplate.from_template("""
            You are an expert at creating personalized cover letters for job applications.
            Generate compelling talking points for a cover letter based on how a candidate's profile matches a job description.
            
            JOB FEATURES:
            {job_features}
            
            CANDIDATE FEATURES:
            {resume_features}
            
            MATCH ANALYSIS:
            {match_results}
            
            Generate 5-7 specific talking points that highlight:
            1. The candidate's relevant skills and experiences for this specific role
            2. How the candidate's past achievements demonstrate value for this position
            3. Why the candidate is particularly suited for this company/role
            4. How the candidate addresses any potential gaps in skills or experience
            5. The candidate's enthusiasm and interest in this specific role
            
            Each talking point should be concise (1-2 sentences) and highly specific to this job and candidate.
            Focus on the most compelling matches between the candidate's experience and the job requirements.
            Avoid generic points that could apply to any job or candidate.
            
            Return the result as a JSON array of strings.
            """)
            
            # Convert features to strings for the prompt
            job_features_str = json.dumps(job_features, indent=2)
            resume_features_str = json.dumps(resume_features, indent=2)
            match_results_str = json.dumps(match_results, indent=2)
            
            # Generate response
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "job_features": job_features_str,
                "resume_features": resume_features_str,
                "match_results": match_results_str
            })
            
            # Parse JSON response
            try:
                # Extract text content from response
                if hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = str(response)
                    
                # Clean up response to ensure valid JSON
                # Look for array
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    talking_points = json.loads(json_text)
                    
                    if isinstance(talking_points, list):
                        return talking_points
                    else:
                        logger.warning("Response was not a list of talking points")
                        return []
                else:
                    logger.warning("Couldn't extract valid JSON array from talking points response")
                    return []
                    
            except json.JSONDecodeError:
                logger.error("Error parsing JSON from talking points response")
                return []
                
        except Exception as e:
            logger.error(f"Error generating cover letter points: {e}")
            return []

# Example usage
async def main():
    # Sample configuration
    config = {
        "ai": {
            "llm_model": "gpt-4-turbo",
            "temperature": 0.2,
            "max_tokens": 4096,
            "match_threshold": 70
        }
    }
    
    # Initialize analyzer
    analyzer = JobAnalyzer(config)
    await analyzer.initialize()
    
    # Sample job description
    job_description = """
    Senior Software Engineer - Python/AWS
    
    We are looking for a Senior Software Engineer with strong Python skills and AWS experience.
    The ideal candidate will have 5+ years of experience in software development, with at least 3 years working with Python.
    
    Required Skills:
    - Python
    - AWS (EC2, S3, Lambda)
    - REST API design and implementation
    - Git
    - CI/CD pipelines
    
    Preferred Skills:
    - Kubernetes
    - Docker
    - Terraform
    - Microservices architecture
    
    Responsibilities:
    - Design and implement scalable backend services
    - Maintain and improve existing systems
    - Collaborate with cross-functional teams
    - Mentor junior developers
    
    Education:
    - Bachelor's degree in Computer Science or related field
    """
    
    # Sample resume data
    resume_data = {
        "basic_info": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "123-456-7890"
        },
        "skills": [
            "Python",
            "JavaScript",
            "AWS",
            "Docker",
            "Git",
            "REST APIs",
            "SQL"
        ],
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Company",
                "start_date": "2018-01",
                "end_date": "2022-12",
                "description": "Developed backend services using Python and AWS.",
                "achievements": [
                    "Reduced API response time by 30%",
                    "Implemented CI/CD pipeline"
                ],
                "technologies": [
                    "Python",
                    "AWS",
                    "Docker",
                    "Git"
                ]
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "institution": "University",
                "date": "2017"
            }
        ]
    }
    
    # Analyze job
    analysis = await analyzer.analyze_job(job_description, resume_data)
    print(f"Match Score: {analysis.get('match_score')}")
    print(f"Matching Skills: {analysis.get('matching_skills')}")
    print(f"Missing Skills: {analysis.get('missing_skills')}")
    print(f"Assessment: {analysis.get('assessment')}")
    print(f"Cover Letter Points: {analysis.get('cover_letter_points')}")

if __name__ == "__main__":
    asyncio.run(main())
