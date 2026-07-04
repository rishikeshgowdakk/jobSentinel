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

    def get_embedding(self, text: str) -> list:
        if not self.client or not text:
            return []
        try:
            # Clean text up to fit in token limit of embeddings
            truncated_text = text[:1500]
            response = self.client.models.embed_content(
                model="text-embedding-004",
                contents=truncated_text
            )
            if hasattr(response, 'embeddings') and len(response.embeddings) > 0:
                return response.embeddings[0].values
            elif hasattr(response, 'embedding') and hasattr(response.embedding, 'values'):
                return response.embedding.values
            return []
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    def extract_resume_parameters(self, resume_text: str) -> dict:
        if not self.client:
            logger.warning("Gemini Client not initialized for resume extraction. Using defaults.")
            return {
                "name": "Candidate Profile",
                "email": "candidate@example.com",
                "phone": "+1-234-567-8900",
                "location": "San Francisco, CA",
                "yoe": 2,
                "current_role": "Software Engineer",
                "previous_roles": ["Junior Developer"],
                "skills": ["Python", "FastAPI", "React", "Docker", "PostgreSQL"],
                "frameworks": ["React", "FastAPI", "Express"],
                "languages": ["Python", "JavaScript", "SQL"],
                "cloud_platforms": ["AWS"],
                "devops_tools": ["Docker", "GitHub Actions"],
                "aiml_skills": ["Scikit-Learn"],
                "databases": ["PostgreSQL", "Redis"],
                "projects": ["Job Aggregator App", "Portfolio Website"],
                "education": ["BS in Computer Science"],
                "certifications": ["AWS Cloud Practitioner"],
                "preferred_locations": ["Remote", "San Francisco"],
                "work_authorization": "Authorized to work in US",
                "remote_preference": "Remote",
                "internship_or_fulltime": "Full-Time",
                "expected_graduation": "",
                "seniority_level": "Mid Level"
            }
        
        prompt = f"""
        Analyze the following resume and extract the structured parameters.
        
        Resume Content:
        {resume_text}
        
        Output a JSON object with EXACTLY the following keys:
        - name: (string)
        - email: (string)
        - phone: (string)
        - location: (string)
        - yoe: (int) Total years of professional experience
        - current_role: (string) Current job title
        - previous_roles: [list of strings]
        - skills: [list of strings]
        - frameworks: [list of strings]
        - languages: [list of strings]
        - cloud_platforms: [list of strings]
        - devops_tools: [list of strings]
        - aiml_skills: [list of strings]
        - databases: [list of strings]
        - projects: [list of strings / summaries]
        - education: [list of strings]
        - certifications: [list of strings]
        - preferred_locations: [list of strings]
        - work_authorization: (string)
        - remote_preference: (string) e.g., Remote, Hybrid, Onsite
        - internship_or_fulltime: (string) e.g., Internship, Full-Time, Contract
        - expected_graduation: (string)
        - seniority_level: (string) e.g., Entry Level, Mid Level, Senior Level, Principal
        
        Ensure output is raw JSON, valid and complete. Do not include markdown code block formatting in your JSON output.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error extracting resume parameters: {e}")
            return {
                "name": "Failed Parse",
                "email": "",
                "phone": "",
                "location": "Remote",
                "yoe": 0,
                "current_role": "Developer",
                "previous_roles": [],
                "skills": ["Developer"],
                "frameworks": [],
                "languages": [],
                "cloud_platforms": [],
                "devops_tools": [],
                "aiml_skills": [],
                "databases": [],
                "projects": [],
                "education": [],
                "certifications": [],
                "preferred_locations": [],
                "work_authorization": "",
                "remote_preference": "Remote",
                "internship_or_fulltime": "Full-Time",
                "expected_graduation": "",
                "seniority_level": "Entry Level"
            }

    def analyze_job_semantic(self, profile: dict, job_title: str, job_description: str, target_seniority: str = "All", target_job_type: str = "All") -> dict:
        if not self.client:
            logger.warning("Gemini Client not initialized. Using basic semantic matcher.")
            # Simple keyword overlap calculation for local testing without key
            user_skills = set([s.lower() for s in profile.get('skills', [])])
            job_desc_lower = job_description.lower() if job_description else ""
            matched_skills = [s for s in profile.get('skills', []) if s.lower() in job_desc_lower or s.lower() in job_title.lower()]
            missing_skills = [s for s in ["Kubernetes", "Kafka", "Terraform", "AWS", "TypeScript"] if s.lower() not in user_skills][:2]
            
            score = 60 + int(len(matched_skills) * 8)
            score = min(max(score, 0), 100)
            
            return {
                "matchScore": score,
                "confidence": 0.8,
                "matchedSkills": matched_skills[:5],
                "missingSkills": missing_skills,
                "recommendationReason": f"Standard matching based on matching keywords: {', '.join(matched_skills[:3])}.",
                "priority": "High" if score >= 80 else ("Medium" if score >= 60 else "Low"),
                "applyImmediately": score >= 80
            }

        sd = profile.get("structured_data", {})
        skills_str = ", ".join(sd.get("skills", []))
        languages_str = ", ".join(sd.get("languages", []))
        yoe = sd.get("yoe", 0)

        prompt = f"""
        You are an expert AI recruiter matching a candidate to a job.
        
        Candidate Profile:
        - Years of Experience: {yoe}
        - Current Role: {sd.get("current_role", "")}
        - Primary Skills: {skills_str}
        - Languages: {languages_str}
        - Projects: {', '.join(sd.get("projects", []))}
        
        Job Posting:
        - Title: {job_title}
        - Description: {job_description}
        
        User Search Preferences:
        - Target Seniority: {target_seniority}
        - Target Job Type: {target_job_type}
        
        Evaluate the match and return a JSON object with this EXACT structure:
        {{
            "matchScore": (int 0-100),
            "confidence": (float 0.0-1.0),
            "matchedSkills": ["skill1", "skill2", ...],
            "missingSkills": ["missing_skill1", ...],
            "recommendationReason": "Why this job matches (2-3 sentences explaining strong alignments or project similarities)",
            "priority": "High" / "Medium" / "Low",
            "applyImmediately": (true/false)
        }}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error in deep matching: {e}")
            return {
                "matchScore": 60,
                "confidence": 0.5,
                "matchedSkills": [],
                "missingSkills": [],
                "recommendationReason": "Fallback match based on parse exception.",
                "priority": "Medium",
                "applyImmediately": False
            }

    def generate_market_insights(self, jobs: list) -> dict:
        if not self.client or not jobs:
            return {
                "marketDemandScore": 78,
                "trendingSkills": ["Docker", "FastAPI", "Playwright", "React", "PostgreSQL"],
                "averageSalary": "₹12L - ₹24L L.P.A",
                "mostHiringCompanies": ["Infosys", "Randstad", "Flexm", "Nike"],
                "insightsSummary": "The market is showing steady hiring activities in Node.js, Python frameworks, and DevOps tools. React developers are heavily favored."
            }

        job_summaries = "\n".join([f"- {j['title']} at {j['company']} ({j.get('location', '')})" for j in jobs[:20]])
        prompt = f"""
        Analyze the following active job market listings and generate insights:
        
        Job Listings:
        {job_summaries}
        
        Provide a JSON object containing:
        - marketDemandScore: (int 0-100)
        - trendingSkills: [list of 5 strings]
        - averageSalary: (string) e.g. "$120,000 - $160,000"
        - mostHiringCompanies: [list of 4 strings]
        - insightsSummary: (string) A 2-sentence summary of the market trends.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error generating market insights: {e}")
            return {
                "marketDemandScore": 75,
                "trendingSkills": ["Python", "FastAPI", "TypeScript"],
                "averageSalary": "$110,000",
                "mostHiringCompanies": [],
                "insightsSummary": "Failed to parse AI insights."
            }

    def generate_learning_recommendations(self, missing_skills: list) -> list:
        if not self.client or not missing_skills:
            return [
                {
                    "skill": "Docker",
                    "course": "Docker Mastery (Udemy)",
                    "project": "Build a multi-container microservice system on local cluster",
                    "certification": "Docker Certified Associate",
                    "roi": "High (Requested in 84% of postings)",
                    "learningTime": "2 weeks"
                }
            ]

        prompt = f"""
        For each of these missing technical skills, suggest actionable learning resources.
        Missing Skills: {', '.join(missing_skills)}
        
        Output a JSON array of objects, where each object contains:
        - skill: (string)
        - course: (string) Course suggestion
        - project: (string) Practical project idea
        - certification: (string) Recommended certification
        - roi: (string) Return-on-investment estimation
        - learningTime: (string) e.g., '3 weeks'
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error generating learning recommendations: {e}")
            return []

    def generate_resume_suggestions(self, profile: dict, jobs: list) -> dict:
        if not self.client or not profile or not jobs:
            return {
                "missingKeywords": ["Docker", "Kubernetes", "CI/CD Pipeline"],
                "atsImprovements": "Add impact metrics (e.g. 'reduced latency by 20%') instead of list of responsibilities.",
                "projectImprovements": "Include a backend distributed architecture project showing Redis caching and Kafka queue.",
                "grammarFixes": "Use active verbs like 'Designed', 'Orchestrated', and 'Optimized' at start of bullets."
            }

        job_requirements = "\n".join([f"- {j['title']}: {j.get('skills', '')}" for j in jobs[:10]])
        sd = profile.get("structured_data", {})
        
        prompt = f"""
        Compare the candidate's parsed profile against the active job listings:
        
        Candidate Profile:
        {json.dumps(sd, indent=2)}
        
        Active Job Requirements:
        {job_requirements}
        
        Identify gaps and provide actionable resume enhancements.
        Output a JSON object:
        {{
            "missingKeywords": ["kw1", "kw2", ...],
            "atsImprovements": "Detailed critique/advice for ATS parsing",
            "projectImprovements": "Idea for a project that would make the profile highly attractive",
            "grammarFixes": "Verb choice or spacing improvements"
        }}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            return json.loads(text.strip())
        except Exception as e:
            logger.error(f"Error generating resume suggestions: {e}")
            return {
                "missingKeywords": [],
                "atsImprovements": "",
                "projectImprovements": "",
                "grammarFixes": ""
            }
