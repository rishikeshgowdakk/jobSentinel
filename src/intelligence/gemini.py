import json
from google import genai
from src.core.config import config
from src.core.logger import logger

class GeminiAnalyzer:
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = 'gemini-1.5-flash'

    def analyze_job(self, master_resume: str, job_description: str, user_yoe: int = 0, user_tech_stack: list = None, target_seniority: str = "All", target_job_type: str = "All"):
        tech_stack_str = ", ".join(user_tech_stack) if user_tech_stack else "Not specified"
        
        # Human-readable seniority/job type for the prompt
        seniority_map = {"2": "Fresher/Entry Level", "4": "Mid-Senior Level"}
        job_type_map = {"F": "Full-time", "P": "Part-time", "I": "Internship"}
        
        target_seniority_str = seniority_map.get(target_seniority, "Any")
        target_job_type_str = job_type_map.get(target_job_type, "Any")

        prompt = f"""
        You are an expert ATS (Applicant Tracking System) optimizer and career coach. 
        Compare the following Master Resume with the Job Description.
        
        Candidate Profile:
        - Years of Experience: {user_yoe}
        - Primary Tech Stack: {tech_stack_str}
        
        User Search Preferences:
        - Target Seniority: {target_seniority_str}
        - Target Job Type: {target_job_type_str}
        
        Master Resume:
        {master_resume}
        
        Job Description:
        {job_description}
        
        STRICT MATCHING RULES:
        1. SENIORITY MATCH: If Target Seniority is 'Fresher/Entry Level' and the JD requires more than 2 years of experience, set 'ats_score' to 0. 
        2. JOB TYPE MATCH: If Target Job Type is 'Internship' and the JD is for a permanent/senior role, set 'ats_score' to 0.
        3. EXPERIENCE MATCH: If the Job Description explicitly requires significantly more years of experience than the candidate has, the 'ats_score' MUST be 0.
        4. TECH MATCH: If the Job Description mandates a core technology that is completely missing from the candidate's Resume, the 'ats_score' MUST be 0.
        5. If it's a good match, provide a high 'ats_score' and tailored content.
        
        Output a JSON object:
        {{
            "ats_score": (int 0-100),
            "rejection_reason": "Brief reason if score is 0, otherwise null",
            "tailored_summary": "A professional summary tailored to this JD",
            "tailored_experience": [
                {{
                    "company": "Company Name",
                    "role": "Role Name",
                    "bullets": ["tailored bullet 1", "tailored bullet 2"]
                }}
            ],
            "top_skills": ["skill1", "skill2", "skill3"]
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error in Gemini analysis: {e}")
            return None

    def extract_resume_parameters(self, resume_text: str):
        prompt = f"""
        Analyze the following resume and extract key search parameters for a job search.
        
        Resume:
        {resume_text}
        
        Output a JSON object with the following structure:
        {{
            "location": "The user's current or target city/region (e.g., 'San Francisco', 'Remote', 'London')",
            "yoe": (int) Total years of professional experience,
            "tech_stack": ["Primary Technology 1", "Primary Technology 2", ...]
        }}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error extracting resume parameters: {e}")
            return {
                "location": "Remote",
                "yoe": 0,
                "tech_stack": ["Software Engineer"]
            }
