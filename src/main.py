import asyncio
import os
import time
import math
from src.core.config import config
from src.core.logger import logger
from src.core.db import db
from src.scraper.engine import JobScraper
from src.intelligence.gemini import GeminiAnalyzer
from src.notify.email_client import EmailClient

def calculate_cosine_similarity(v1, v2):
    if not v1 or not v2:
        return 0.0
    dot_product = sum(x*y for x, y in zip(v1, v2))
    magnitude1 = math.sqrt(sum(x*x for x in v1))
    magnitude2 = math.sqrt(sum(x*x for x in v2))
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

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
            
            # Consolidated search keywords and locations to minimize WAF blockages/rate limits
            consolidated_keywords = set()
            consolidated_locations = set()
            
            # Keep track of individual preferences to filter matching
            user_prefs_map = {}
            for p in profiles:
                uid = p["user_id"]
                prefs = db.get_user_preferences(uid)
                user_prefs_map[uid] = prefs
                
                for k in prefs["keywords"].split(","):
                    if k.strip(): consolidated_keywords.add(k.strip())
                for l in prefs["locations"].split(","):
                    if l.strip(): consolidated_locations.add(l.strip())
            
            keywords_list = list(consolidated_keywords) if consolidated_keywords else [config.JOB_KEYWORDS]
            locations_list = list(consolidated_locations) if consolidated_locations else [config.JOB_LOCATIONS]
            
            logger.info(f"HUNT CYCLE START: Scrape union of Keywords={keywords_list} | Locations={locations_list} for {len(profiles)} active profiles")
            
            # 2. Scrape platforms in parallel
            tasks = [
                scraper.scrape_linkedin(keywords_list, locations_list),
                scraper.scrape_naukri(keywords_list, locations_list),
                scraper.scrape_google_xray(keywords_list, locations_list)
            ]
            
            platform_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_found_jobs = []
            
            for res in platform_results:
                if isinstance(res, list):
                    all_found_jobs.extend(res)
                elif isinstance(res, Exception):
                    logger.error(f"Platform scraper error: {res}")
            
            # 3. Fallback to mock jobs if live search yielded minimal results
            if len(all_found_jobs) < 4:
                logger.info("Live job listings are limited. Generating fresh mock opportunities for testing...")
                mock_jobs = scraper.generate_mock_jobs(keywords_list)
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
                            user_email = p.get("structured_data", {}).get("email")
                            if user_email:
                                email_client.send_notification(job, match_analysis, recipient_email=user_email)
                            else:
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
