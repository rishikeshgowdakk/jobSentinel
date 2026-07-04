import json
from google import genai
from src.core.config import config
from src.core.logger import logger

class GeminiAnalyzer:
    def __init__(self):
        self.client = None
        if config.GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=config.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client: {e}")
        self.model_name = 'gemini-1.5-flash'

    def analyze_job(self, job_title: str, job_description: str, target_seniority: str = "All", target_job_type: str = "All"):
        # Graceful fallback if API key is not configured or client initialization failed
        if not self.client:
            logger.warning("Gemini API key not configured. Using basic parsing fallback.")
            summary = job_description[:150] + "..." if job_description else "No description available."
            return {
                "is_match": True,
                "match_reason": "Skipped AI matching (no API key)",
                "summary": summary,
                "skills": ["Software"]
            }

        seniority_map = {"2": "Fresher/Entry Level", "4": "Mid-Senior Level"}
        job_type_map = {"F": "Full-time", "P": "Part-time", "I": "Internship"}
        
        target_seniority_str = seniority_map.get(target_seniority, "Any")
        target_job_type_str = job_type_map.get(target_job_type, "Any")

        prompt = f"""
        You are an expert technical recruiter. 
        Analyze the following Job Posting.
        
        Job Title: {job_title}
        Job Description: {job_description}
        
        User Search Preferences:
        - Target Seniority: {target_seniority_str}
        - Target Job Type: {target_job_type_str}
        
        Analyze the job description and:
        1. Extract the top 5 technical skills required for this role.
        2. Generate a professional, exciting 2-sentence summary of the job.
        3. Match Job Type: Check if it matches the user's target job type.
        4. Match Seniority: Check if the required experience matches the user's target seniority.
        
        Output a JSON object:
        {{
            "is_match": (true/false),
            "match_reason": "Why it matches or why it was rejected",
            "summary": "Concise 2-sentence summary",
            "skills": ["skill1", "skill2", "skill3", "skill4", "skill5"]
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
            summary = job_description[:150] + "..." if job_description else "No description available."
            return {
                "is_match": True,
                "match_reason": f"Fallback match due to API error: {e}",
                "summary": summary,
                "skills": []
            }
