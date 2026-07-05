import asyncio
import os
import time
from src.core.config import config
from src.core.logger import logger
from src.core.db import db
from src.core.utils import calculate_cosine_similarity
from src.scraper.engine import JobScraper
from src.intelligence.gemini import GeminiAnalyzer
from src.notify.email_client import EmailClient

async def run_scanner(broadcast_callback=None):
    logger.info("Initializing JobSentinel Autonomous Agent Loop...")
    
    scraper = JobScraper()
    analyzer = GeminiAnalyzer()
    email_client = EmailClient()
    
    while True:
        try:
            # 1. Fetch all user profiles to run scans and evaluations
            profiles = db.get_all_users_profiles()
            if not profiles:
                # Default fallback profile to keep scanner active with defaults if no users are registered
                profiles = [{
                    "user_id": "default_user",
                    "raw_text": "",
                    "structured_data": {},
                    "embedding": []
                }]
            
            user_prefs_map = {}
            all_found_jobs = []
            
            # 2. Scrape platforms per profile
            for p in profiles:
                uid = p["user_id"]
                prefs = db.get_user_preferences(uid)
                user_prefs_map[uid] = prefs
                
                k_list = [k.strip() for k in prefs["keywords"].split(",") if k.strip()] or [config.JOB_KEYWORDS]
                l_list = [l.strip() for l in prefs["locations"].split(",") if l.strip()] or [config.JOB_LOCATIONS]
                
                jtype = "I" if prefs.get("job_type", "All") == "I" or any("intern" in k.lower() for k in k_list) else "All"
                elevel = "2" if prefs.get("experience_level", "All") == "2" or jtype == "I" else "All"
                
                logger.info(f"HUNT CYCLE START for {uid}: Keywords={k_list} | Locations={l_list} | Type={jtype}")
                
                tasks = [
                    scraper.scrape_linkedin(k_list, l_list, jtype, elevel),
                    scraper.scrape_naukri(k_list, l_list, jtype, elevel),
                    scraper.scrape_google_xray(k_list, l_list, jtype, elevel)
                ]
                
                platform_results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in platform_results:
                    if isinstance(res, list):
                        all_found_jobs.extend(res)
                    elif isinstance(res, Exception):
                        logger.error(f"Platform scraper error: {res}")
            
            # 3. Fallback to mock jobs if live search yielded minimal results
            if len(all_found_jobs) < 4:
                logger.info("Live job listings are limited. Generating fresh mock opportunities for testing...")
                k_list = [k.strip() for k in user_prefs_map.get(profiles[0]["user_id"], {}).get("keywords", "").split(",")] if profiles else [config.JOB_KEYWORDS]
                mock_jobs = scraper.generate_mock_jobs(k_list)
                all_found_jobs.extend(mock_jobs)
            
            logger.info(f"Aggregated {len(all_found_jobs)} jobs. Analyzing opportunities...")
            
            # 4. Process each job
            for job in all_found_jobs:
                try:
                    # Skip duplicate check based on URL or title+company
                    if db.job_exists(job['job_id']):
                        continue
                    
                    logger.info(f"Analyzing Job Opportunity globally: {job['title']} at {job['company']}")
                    
                    job_embedding = analyzer.get_embedding(job['title'] + " " + job['description'])
                    # Save the job globally
                    db.add_job(job, job_embedding)
                    
                    # 5. Evaluate and save match score for each user
                    for p in profiles:
                        uid = p["user_id"]
                        prefs = user_prefs_map.get(uid, {})
                        
                        match_analysis = {}
                        if p.get("raw_text"):
                            # Deep LLM analysis
                            match_analysis = analyzer.analyze_job_semantic(
                                profile=p,
                                job_title=job['title'],
                                job_description=job['description'],
                                target_seniority=prefs.get("experience_level", "All"),
                                target_job_type=prefs.get("job_type", "All")
                            )
                            # Vector cosine similarity
                            vector_sim = calculate_cosine_similarity(job_embedding, p.get('embedding', []))
                            
                            # Combine vector and semantic score
                            semantic_score = match_analysis.get('matchScore', 60)
                            combined_score = int(0.25 * (vector_sim * 100) + 0.75 * semantic_score)
                            combined_score = min(max(combined_score, 0), 100)
                            
                            # STRICT ZERO-TOLERANCE ATS FILTERING
                            target_jtype = prefs.get("job_type", "All")
                            target_elevel = prefs.get("experience_level", "All")
                            title_lower = job['title'].lower()
                            
                            if target_jtype == "I" and "intern" not in title_lower and "trainee" not in title_lower:
                                combined_score = 0
                                match_analysis['recommendationReason'] = "ATS Rejected: Does not match Internship requirement."
                            elif target_jtype == "F" and ("intern" in title_lower or "trainee" in title_lower):
                                combined_score = 0
                                match_analysis['recommendationReason'] = "ATS Rejected: Looks like an internship, but full-time requested."
                                
                            if target_elevel == "2" and ("senior" in title_lower or "staff" in title_lower or "principal" in title_lower or "lead" in title_lower or "manager" in title_lower or "sde 3" in title_lower or "sde 4" in title_lower):
                                combined_score = 0
                                match_analysis['recommendationReason'] = "ATS Rejected: Too senior for your Entry/Junior preference."
                            elif target_elevel == "4" and ("intern" in title_lower or "junior" in title_lower or "fresher" in title_lower or "entry" in title_lower):
                                combined_score = 0
                                match_analysis['recommendationReason'] = "ATS Rejected: Too junior for your Senior preference."
                            
                            match_analysis['matchScore'] = combined_score
                            match_analysis['job_id'] = job['job_id']
                        else:
                            # Default matcher if profile isn't uploaded yet
                            match_analysis = {
                                "job_id": job['job_id'],
                                "matchScore": 0,
                                "confidence": 1.0,
                                "matchedSkills": [],
                                "missingSkills": [],
                                "recommendationReason": "Upload your resume in the profile tab to enable personalized semantic matching.",
                                "priority": "Medium",
                                "applyImmediately": False
                            }
                        
                        # Save match for this specific user
                        db.save_match(uid, match_analysis)
                        
                        # Trigger notification if Match Score >= 80 for this user
                        if match_analysis.get('matchScore', 0) >= 80:
                            # Send notifications using user details if available
                            email_client.send_notification(job, match_analysis)
                        
                        # Broadcast new job discovery to this user's socket connections
                        if broadcast_callback:
                            broadcast_data = {**job, **match_analysis}
                            await broadcast_callback(uid, {"type": "new_job", "data": broadcast_data})
                            
                except Exception as job_e:
                    logger.error(f"Error processing job {job.get('job_id')}: {job_e}")
                    continue
            
            logger.info(f"Hunt cycle completed. Sleeping {config.SCRAPE_INTERVAL}s...")
            await asyncio.sleep(config.SCRAPE_INTERVAL)
            
        except Exception as e:
            logger.error(f"Scanner Loop Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(run_scanner())
