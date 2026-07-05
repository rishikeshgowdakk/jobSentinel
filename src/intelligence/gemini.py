import json
from google import genai
from src.core.config import config
from src.core.logger import logger

class GeminiAnalyzer:
    def __init__(self):
        self.client = None
        api_key = config.GEMINI_API_KEY
        if api_key and not api_key.startswith("your_") and api_key != "your_gemini_api_key":
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client: {e}")
        else:
            logger.warning("No valid Gemini API key detected. Running in local fallback mode.")
        self.model_name = 'gemini-2.0-flash'

    def get_embedding(self, text: str) -> list:
        if not self.client or not text:
            return []
        try:
            # Clean text up to fit in token limit of embeddings
            truncated_text = text[:1500]
            response = self.client.models.embed_content(
                model="gemini-embedding-2",
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
            logger.warning("Gemini Client not initialized for resume extraction. Using local rule-based fallback parser.")
            
            import re
            lines = [line.strip() for line in resume_text.split('\n') if line.strip()]
            
            name = "Candidate Profile"
            for line in lines[:4]:
                if "@" not in line and not any(char.isdigit() for char in line) and len(line.split()) <= 4:
                    name = line
                    break
                    
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
            email = email_match.group(0) if email_match else ""
            
            phone_match = re.search(r'\(?\+?[0-9]{1,4}\)?[-\s\./0-9]{7,15}', resume_text)
            phone = phone_match.group(0).strip() if phone_match else ""
            
            location = "Remote"
            loc_match = re.search(r'([A-Z][a-zA-Z\s]+,\s*[A-Z]{2,3}|[A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+)', resume_text)
            if loc_match:
                location = loc_match.group(0).strip()
            
            yoe = 0
            yoe_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)', resume_text, re.IGNORECASE)
            if yoe_match:
                yoe = int(yoe_match.group(1))
            else:
                exp_words = re.findall(r'(\d+)\s*(?:years?|yrs?)', resume_text, re.IGNORECASE)
                if exp_words:
                    try:
                        yoe = max(int(w) for w in exp_words if int(w) < 30)
                    except ValueError:
                        pass

            tech_dictionary = {
                "skills": ["python", "fastapi", "react", "docker", "postgresql", "kubernetes", "golang", "typescript", "javascript", "aws", "terraform", "django", "flask", "node.js", "express", "sql", "redis", "mongodb", "mysql", "java", "spring boot", "git", "ci/cd", "html", "css", "vue", "angular", "next.js", "c++", "c#"],
                "frameworks": ["react", "fastapi", "express", "django", "flask", "spring boot", "vue", "angular", "next.js", "laravel", "rails"],
                "languages": ["python", "javascript", "typescript", "golang", "java", "c++", "c#", "ruby", "php", "rust", "sql", "html", "css"],
                "cloud_platforms": ["aws", "gcp", "azure", "heroku", "digitalocean", "cloudflare"],
                "devops_tools": ["docker", "kubernetes", "terraform", "jenkins", "ansible", "github actions", "gitlab ci", "prometheus", "grafana"],
                "databases": ["postgresql", "redis", "mongodb", "mysql", "sqlite", "cassandra", "dynamodb", "elasticsearch"],
                "aiml_skills": ["tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy", "opencv", "nlp", "llm"]
            }

            extracted = {k: [] for k in tech_dictionary.keys()}
            resume_lower = resume_text.lower()
            
            for category, keywords in tech_dictionary.items():
                for kw in keywords:
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    if re.search(pattern, resume_lower):
                        formatted = kw.upper() if kw in ["aws", "gcp", "sql", "html", "css", "nlp", "llm", "api"] else kw.capitalize()
                        if kw == "node.js": formatted = "Node.js"
                        if kw == "next.js": formatted = "Next.js"
                        if kw == "spring boot": formatted = "Spring Boot"
                        if kw == "github actions": formatted = "GitHub Actions"
                        if kw == "gitlab ci": formatted = "GitLab CI"
                        if kw == "scikit-learn": formatted = "Scikit-Learn"
                        extracted[category].append(formatted)

            all_skills = list(set(
                extracted["skills"] + 
                extracted["frameworks"] + 
                extracted["languages"] + 
                extracted["cloud_platforms"] + 
                extracted["devops_tools"] + 
                extracted["databases"] + 
                extracted["aiml_skills"]
            ))
            if not all_skills:
                all_skills = ["Developer"]

            projects = []
            education = []
            
            project_keywords = ["project", "portfolio", "application", "system", "app"]
            edu_keywords = ["bs", "ms", "phd", "bachelor", "master", "degree", "university", "college", "institute", "school"]
            
            for line in lines:
                line_lower = line.lower()
                if any(kw in line_lower for kw in project_keywords) and len(line) > 10 and len(line) < 100:
                    projects.append(line)
                if any(kw in line_lower for kw in edu_keywords) and len(line) > 10 and len(line) < 100:
                    education.append(line)

            projects = list(dict.fromkeys(projects))[:4]
            education = list(dict.fromkeys(education))[:3]

            seniority = "Entry Level"
            if yoe >= 5: seniority = "Senior Level"
            elif yoe >= 3: seniority = "Mid Level"

            return {
                "name": name,
                "email": email or "candidate@example.com",
                "phone": phone or "+1-234-567-8900",
                "location": location,
                "yoe": yoe,
                "current_role": name if name != "Candidate Profile" else "Software Engineer",
                "previous_roles": [],
                "skills": all_skills,
                "frameworks": extracted["frameworks"],
                "languages": extracted["languages"],
                "cloud_platforms": extracted["cloud_platforms"],
                "devops_tools": extracted["devops_tools"],
                "aiml_skills": extracted["aiml_skills"],
                "databases": extracted["databases"],
                "projects": projects if projects else ["Personal Projects"],
                "education": education if education else ["Self-taught Developer"],
                "certifications": [],
                "preferred_locations": [location] if location != "Remote" else ["Remote"],
                "work_authorization": "Authorized to work in US" if "authorized" in resume_lower or "citizen" in resume_lower or "green card" in resume_lower else "Not Specified",
                "remote_preference": "Remote" if "remote" in resume_lower or "work from home" in resume_lower else "Onsite",
                "internship_or_fulltime": "Full-Time" if "fulltime" in resume_lower or "full-time" in resume_lower or "permanent" in resume_lower else "Contract",
                "expected_graduation": "",
                "seniority_level": seniority
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
        total_jobs = len(jobs)
        if total_jobs == 0:
            return {
                "marketDemandScore": 0,
                "trendingSkills": [],
                "averageSalary": "N/A",
                "mostHiringCompanies": [],
                "insightsSummary": "No job listings scraped yet. Real-time intelligence will populate as scanning proceeds.",
                "experienceDemands": {"junior": 0, "mid": 0, "senior": 0},
                "jobTypeDemands": {"internship": 0, "fulltime": 0, "contract": 0}
            }

        # 1. Count skills
        import re
        from collections import Counter
        
        tech_words = [
            "Python", "FastAPI", "React", "Docker", "PostgreSQL", "Kubernetes", "Golang", "TypeScript", 
            "JavaScript", "AWS", "Terraform", "Django", "Flask", "Node.js", "Express", "SQL", "Redis", 
            "MongoDB", "MySQL", "Java", "Spring Boot", "Git", "CI/CD", "Next.js", "C++", "C#", "Rust",
            "Tailwind", "Machine Learning", "PyTorch", "TensorFlow", "Pandas", "Kafka"
        ]
        
        skills_counter = Counter()
        for j in jobs:
            # Check explicit skills
            exp_skills = j.get("skills", "")
            if exp_skills:
                for s in exp_skills.split(","):
                    s_clean = s.strip()
                    if s_clean:
                        # Find correct casing
                        matched_casing = next((w for w in tech_words if w.lower() == s_clean.lower()), s_clean)
                        skills_counter[matched_casing] += 1
            # Also search description and title
            desc = (j.get("description", "") or "").lower()
            title = (j.get("title", "") or "").lower()
            for word in tech_words:
                pattern = r'\b' + re.escape(word.lower()) + r'\b'
                if re.search(pattern, desc) or re.search(pattern, title):
                    skills_counter[word] += 1

        trending = [item[0] for item in skills_counter.most_common(8)]
        if not trending:
            trending = ["Python", "FastAPI", "React", "Docker", "PostgreSQL"]

        # 2. Count hiring companies
        company_counter = Counter()
        for j in jobs:
            comp = j.get("company")
            if comp and comp != "N/A":
                company_counter[comp] += 1
        most_hiring = [item[0] for item in company_counter.most_common(4)]

        # 3. Analyze salaries
        salaries = []
        for j in jobs:
            sal = j.get("salary", "")
            if sal and any(char.isdigit() for char in sal):
                salaries.append(sal)
        
        if salaries:
            unique_sals = list(set(salaries))
            if len(unique_sals) > 1:
                avg_salary = f"{unique_sals[0]} - {unique_sals[min(len(unique_sals)-1, 3)]}"
            else:
                avg_salary = unique_sals[0]
        else:
            avg_salary = "Competitive (Not Disclosed)"

        # 4. Experience demands
        junior_cnt = 0
        mid_cnt = 0
        senior_cnt = 0
        
        for j in jobs:
            exp_str = (j.get("experience", "") or "").lower()
            title_str = (j.get("title", "") or "").lower()
            desc_str = (j.get("description", "") or "").lower()
            
            if any(x in exp_str for x in ["0-1", "0-2", "fresher", "junior", "entry", "associate"]) or \
               any(x in title_str for x in ["junior", "associate", "fresher", "entry"]) or \
               "0 years" in desc_str or "1 year" in desc_str or "1+ year" in desc_str:
                junior_cnt += 1
            elif any(x in exp_str for x in ["5+", "6+", "7+", "8+", "senior", "lead", "principal", "manager"]) or \
                 any(x in title_str for x in ["senior", "lead", "principal", "staff"]):
                senior_cnt += 1
            else:
                mid_cnt += 1
                
        total_exp = junior_cnt + mid_cnt + senior_cnt
        if total_exp > 0:
            junior_pct = int((junior_cnt / total_exp) * 100)
            senior_pct = int((senior_cnt / total_exp) * 100)
            mid_pct = 100 - junior_pct - senior_pct
        else:
            junior_pct, mid_pct, senior_pct = 33, 34, 33

        # 5. Job Type demands
        intern_cnt = 0
        ft_cnt = 0
        contract_cnt = 0
        for j in jobs:
            title_str = (j.get("title", "") or "").lower()
            desc_str = (j.get("description", "") or "").lower()
            
            if "intern" in title_str or "internship" in title_str or "intern" in desc_str:
                intern_cnt += 1
            elif "contract" in title_str or "freelance" in title_str or "temporary" in desc_str or "contract" in desc_str:
                contract_cnt += 1
            else:
                ft_cnt += 1
                
        total_types = intern_cnt + ft_cnt + contract_cnt
        if total_types > 0:
            intern_pct = int((intern_cnt / total_types) * 100)
            contract_pct = int((contract_cnt / total_types) * 100)
            ft_pct = 100 - intern_pct - contract_pct
        else:
            intern_pct, ft_pct, contract_pct = 15, 75, 10

        demand_score = min(100, int(total_jobs * 2.5) + 60)

        insights_summary = (
            f"Analyzing {total_jobs} active job listings in the database. "
            f"Currently, {junior_pct}% of roles are open to early career or entry-level talent (0-2 years exp), "
            f"while internships represent {intern_pct}% of the market volume. "
            f"The tech stack trends heavily towards {', '.join(trending[:3])}."
        )

        return {
            "marketDemandScore": demand_score,
            "trendingSkills": trending,
            "averageSalary": avg_salary,
            "mostHiringCompanies": most_hiring if most_hiring else ["Multiple Hirers"],
            "insightsSummary": insights_summary,
            "experienceDemands": {
                "junior": junior_pct,
                "mid": mid_pct,
                "senior": senior_pct
            },
            "jobTypeDemands": {
                "internship": intern_pct,
                "fulltime": ft_pct,
                "contract": contract_pct
            }
        }

    def generate_learning_recommendations(self, missing_skills: list) -> list:
        # Build local catalog for instant dynamic real-time recommendation without API delays
        local_catalog = {
            "Docker": {
                "course": "Docker Mastery: with Kubernetes + Swarm (Udemy)",
                "project": "Containerize a multi-service PostgreSQL & FastAPI app using Docker Compose",
                "certification": "Docker Certified Associate (DCA)",
                "roi": "High (Demanded in 82% of DevOps and Backend positions)",
                "learningTime": "1-2 weeks"
            },
            "Kubernetes": {
                "course": "Certified Kubernetes Administrator (CKA) with Practice Labs (KodeKloud)",
                "project": "Deploy a highly-available auto-scaling web application cluster",
                "certification": "Certified Kubernetes Administrator (CKA)",
                "roi": "Very High (Standard for enterprise orchestration and container management)",
                "learningTime": "3-4 weeks"
            },
            "Kafka": {
                "course": "Apache Kafka Series - Learn Apache Kafka for Beginners v2 (Udemy)",
                "project": "Build a real-time event streaming pipeline processing website clickstreams",
                "certification": "Confluent Certified Developer for Apache Kafka (CCDAK)",
                "roi": "High (Standard for high-throughput stream processing systems)",
                "learningTime": "2 weeks"
            },
            "Terraform": {
                "course": "HashiCorp Certified: Terraform Associate (Udemy)",
                "project": "Provision multi-region AWS network resources and VPC infrastructure via code",
                "certification": "HashiCorp Certified: Terraform Associate",
                "roi": "High (Industry benchmark for Infrastructure as Code)",
                "learningTime": "1-2 weeks"
            },
            "AWS": {
                "course": "AWS Certified Solutions Architect Associate (Stephane Maarek)",
                "project": "Architect a serverless, highly-available React application hosting platform",
                "certification": "AWS Certified Solutions Architect - Associate",
                "roi": "Critical (AWS remains the dominant global cloud computing provider)",
                "learningTime": "4 weeks"
            },
            "FastAPI": {
                "course": "Modern APIs with FastAPI (Talk Python Training)",
                "project": "Build an asynchronous high-performance REST API with OAuth2 and PostgreSQL",
                "certification": "Python Institute Certified Professional",
                "roi": "High (Fastest growing modern python backend framework)",
                "learningTime": "1 week"
            },
            "React": {
                "course": "React - The Complete Guide (Maximilian Schwarzmüller)",
                "project": "Build a fully-responsive interactive dark mode admin dashboard",
                "certification": "Meta Front-End Developer Professional Certificate",
                "roi": "Critical (Top client-side web framework in global demand)",
                "learningTime": "2-3 weeks"
            },
            "Next.js": {
                "course": "Next.js Dev to Deployment (Udemy)",
                "project": "Build a full-stack SEO-optimized server-side-rendered e-commerce platform",
                "certification": "Vercel Next.js Certification",
                "roi": "High (Standard for professional production React applications)",
                "learningTime": "2 weeks"
            },
            "PostgreSQL": {
                "course": "PostgreSQL Bootcamp: Go From Beginner to Advanced (Udemy)",
                "project": "Design and optimize a database schema with indexing and JSONB queries",
                "certification": "PostgreSQL Professional Certification",
                "roi": "High (Most preferred relational database for modern engineering projects)",
                "learningTime": "1 week"
            },
            "Redis": {
                "course": "Redis University - Redis for Python Developers",
                "project": "Implement distributed caching and rate-limiting middleware for your REST API",
                "certification": "Redis Certified Developer",
                "roi": "Medium-High (Universal key-value caching standard)",
                "learningTime": "1 week"
            },
            "TypeScript": {
                "course": "Understanding TypeScript - 2026 Edition (Udemy)",
                "project": "Convert a large Node.js / JavaScript express backend to strict TypeScript type safety",
                "certification": "Microsoft Certified Specialist",
                "roi": "High (Rapidly replacing vanilla JavaScript for backend and frontend scale)",
                "learningTime": "1 week"
            },
            "Python": {
                "course": "Python Deep Dive (Fred Baptiste)",
                "project": "Write custom decorators, asynchronous loops, and memory-efficient generators",
                "certification": "PCAP Certified Associate in Python Programming",
                "roi": "Critical (Ubiquitous language for Web, AI, Data Science)",
                "learningTime": "2 weeks"
            },
            "Golang": {
                "course": "Go: The Complete Developer's Guide (Stephen Grider)",
                "project": "Write a highly-concurrent web crawler utilizing channels and Goroutines",
                "certification": "Google Go Programming Certificate",
                "roi": "High (Dominates microservices infrastructure and cloud-native toolings)",
                "learningTime": "2 weeks"
            },
            "Machine Learning": {
                "course": "Machine Learning Zoomcamp (DataTalksClub)",
                "project": "Train, evaluate, and deploy a random forest classifier to production behind an API",
                "certification": "Google Cloud Professional Machine Learning Engineer",
                "roi": "High (Core foundation for modern AI development pipelines)",
                "learningTime": "4 weeks"
            },
            "Git": {
                "course": "Git & GitHub Complete Guide: Practical Bootcamp (Udemy)",
                "project": "Configure automated git hooks and pull request linting actions",
                "certification": "Git Specialist Certificate",
                "roi": "Standard (Essential for every collaborative developer workflow)",
                "learningTime": "3 days"
            },
            "CI/CD": {
                "course": "GitHub Actions, Travis CI, and Jenkins Pipelines (Udemy)",
                "project": "Write a pipeline that runs tests, builds docker images, and deploys to cloud upon merge",
                "certification": "DevOps Engineer Professional",
                "roi": "High (Crucial skill for modern automated agile deployments)",
                "learningTime": "1 week"
            }
        }

        # If Gemini client is active, we can generate dynamic personalized recommendations
        if self.client:
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

        # Fallback to local catalog
        recommendations = []
        for s in missing_skills:
            # Find closest match or create template
            cat = local_catalog.get(s)
            if not cat:
                # Search case-insensitively
                found = False
                for key, val in local_catalog.items():
                    if key.lower() == s.lower():
                        cat = val
                        found = True
                        break
                if not found:
                    # Dynamic template fallback
                    cat = {
                        "course": f"{s} Complete Bootcamp / Developer Guide (Udemy)",
                        "project": f"Build a prototype demonstrating clean application of {s}",
                        "certification": f"{s} Developer Certificate",
                        "roi": "Medium-High (Demanded in local developer job listings)",
                        "learningTime": "1-2 weeks"
                    }
            recommendations.append({
                "skill": s,
                "course": cat["course"],
                "project": cat["project"],
                "certification": cat["certification"],
                "roi": cat["roi"],
                "learningTime": cat["learningTime"]
            })
        return recommendations

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
