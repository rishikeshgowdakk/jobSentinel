import json
import google.generativeai as genai
from src.core.config import config
from src.core.logger import logger

class GeminiAnalyzer:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def analyze_job(self, master_resume: str, job_description: str):
        prompt = f"""
        You are an expert ATS (Applicant Tracking System) optimizer. 
        Compare the following Master Resume with the Job Description.
        
        Master Resume:
        {master_resume}
        
        Job Description:
        {job_description}
        
        Output a JSON object with the following structure:
        {{
            "ats_score": (int 0-100),
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
        
        Maintain truthfulness while emphasizing relevant keywords from the JD.
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Extract JSON from response (handling potential markdown formatting)
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error in Gemini analysis: {e}")
            return None
