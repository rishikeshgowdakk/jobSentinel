import re

def main():
    with open('src/intelligence/gemini.py', 'r') as f:
        content = f.read()

    # Move tech_dictionary to module level
    tech_dict_code = """
TECH_DICTIONARY = {
    "skills": ["python", "fastapi", "react", "docker", "postgresql", "kubernetes", "golang", "typescript", "javascript", "aws", "terraform", "django", "flask", "node.js", "express", "sql", "redis", "mongodb", "mysql", "java", "spring boot", "git", "ci/cd", "html", "css", "vue", "angular", "next.js", "c++", "c#"],
    "frameworks": ["react", "fastapi", "express", "django", "flask", "spring boot", "vue", "angular", "next.js", "laravel", "rails"],
    "languages": ["python", "javascript", "typescript", "golang", "java", "c++", "c#", "ruby", "php", "rust", "sql", "html", "css"],
    "cloud_platforms": ["aws", "gcp", "azure", "heroku", "digitalocean", "cloudflare"],
    "devops_tools": ["docker", "kubernetes", "terraform", "jenkins", "ansible", "github actions", "gitlab ci", "prometheus", "grafana"],
    "databases": ["postgresql", "redis", "mongodb", "mysql", "sqlite", "cassandra", "dynamodb", "elasticsearch"],
    "aiml_skills": ["tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy", "opencv", "nlp", "llm"]
}
"""
    if "TECH_DICTIONARY = {" not in content:
        content = content.replace("from src.core.logger import logger", "from src.core.logger import logger\n" + tech_dict_code)

    # In extract_resume_parameters: Replace tech_dictionary = {...} with reference to TECH_DICTIONARY
    old_tech_dict_block = """            tech_dictionary = {
                "skills": ["python", "fastapi", "react", "docker", "postgresql", "kubernetes", "golang", "typescript", "javascript", "aws", "terraform", "django", "flask", "node.js", "express", "sql", "redis", "mongodb", "mysql", "java", "spring boot", "git", "ci/cd", "html", "css", "vue", "angular", "next.js", "c++", "c#"],
                "frameworks": ["react", "fastapi", "express", "django", "flask", "spring boot", "vue", "angular", "next.js", "laravel", "rails"],
                "languages": ["python", "javascript", "typescript", "golang", "java", "c++", "c#", "ruby", "php", "rust", "sql", "html", "css"],
                "cloud_platforms": ["aws", "gcp", "azure", "heroku", "digitalocean", "cloudflare"],
                "devops_tools": ["docker", "kubernetes", "terraform", "jenkins", "ansible", "github actions", "gitlab ci", "prometheus", "grafana"],
                "databases": ["postgresql", "redis", "mongodb", "mysql", "sqlite", "cassandra", "dynamodb", "elasticsearch"],
                "aiml_skills": ["tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy", "opencv", "nlp", "llm"]
            }

            extracted = {k: [] for k in tech_dictionary.keys()}"""
    
    new_tech_dict_block = """            extracted = {k: [] for k in TECH_DICTIONARY.keys()}"""
    
    if old_tech_dict_block in content:
        content = content.replace(old_tech_dict_block, new_tech_dict_block)
        content = content.replace("for category, keywords in tech_dictionary.items():", "for category, keywords in TECH_DICTIONARY.items():")

    # In analyze_job_semantic: Rewrite the local fallback logic
    old_semantic_fallback = """            # Simple keyword overlap calculation for local testing without key
            user_skills = set([s.lower() for s in profile.get('skills', [])])
            job_desc_lower = job_description.lower() if job_description else ""
            matched_skills = [s for s in profile.get('skills', []) if s.lower() in job_desc_lower or s.lower() in job_title.lower()]
            missing_skills = [s for s in ["Kubernetes", "Kafka", "Terraform", "AWS", "TypeScript"] if s.lower() not in user_skills][:2]
            
            score = 60 + int(len(matched_skills) * 8)
            score = min(max(score, 0), 100)"""

    new_semantic_fallback = """            # ATS Keyword Extraction & Set Matching (Local ATS Engine)
            job_desc_lower = (job_title + " " + (job_description or "")).lower()
            
            job_required_skills = set()
            import re
            for category, keywords in TECH_DICTIONARY.items():
                for kw in keywords:
                    pattern = r'\\b' + re.escape(kw) + r'\\b'
                    if re.search(pattern, job_desc_lower):
                        formatted = kw.upper() if kw in ["aws", "gcp", "sql", "html", "css", "nlp", "llm", "api"] else kw.capitalize()
                        if kw == "node.js": formatted = "Node.js"
                        if kw == "next.js": formatted = "Next.js"
                        if kw == "spring boot": formatted = "Spring Boot"
                        job_required_skills.add(formatted)
            
            user_skills = set(profile.get('skills', []))
            user_skills_lower = {s.lower() for s in user_skills}
            
            # Map formatted skills to lower for accurate intersection
            matched_skills = []
            missing_skills = []
            
            for req_skill in list(job_required_skills):
                if req_skill.lower() in user_skills_lower:
                    matched_skills.append(req_skill)
                else:
                    missing_skills.append(req_skill)
            
            total_req = len(job_required_skills)
            if total_req == 0:
                score = 80 # default if no tech words found
            else:
                score = int((len(matched_skills) / total_req) * 100)
                
            score = min(max(score, 0), 100)"""

    if old_semantic_fallback in content:
        content = content.replace(old_semantic_fallback, new_semantic_fallback)

    with open('src/intelligence/gemini.py', 'w') as f:
        f.write(content)
        
    print("gemini.py updated successfully.")

if __name__ == '__main__':
    main()
