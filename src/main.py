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
            # 1. Fetch user search preferences & resume profile
            db_keywords = db.get_setting("keywords")
            db_locations = db.get_setting("locations")
            job_type = db.get_setting("job_type", "All")
            exp_level = db.get_setting("experience_level", "All")
            
            keywords = [k.strip() for k in db_keywords.split(",")] if db_keywords else [config.JOB_KEYWORDS]
            locations = [l.strip() for l in db_locations.split(",")] if db_locations else [config.JOB_LOCATIONS]
            
            profile = db.get_profile()

            logger.info(f"HUNT CYCLE START: Keywords={keywords} | Locations={locations} | Type={job_type} | Exp={exp_level}")

            # 2. Scrape platforms in parallel
            tasks = [
                scraper.scrape_linkedin(keywords, locations, job_type, exp_level),
                scraper.scrape_naukri(keywords, locations, job_type, exp_level)
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
                mock_jobs = scraper.generate_mock_jobs(keywords)
                all_found_jobs.extend(mock_jobs)

            logger.info(f"Aggregated {len(all_found_jobs)} jobs. Analyzing opportunities...")

            # 4. Process each job
            for job in all_found_jobs:
                try:
                    # Skip duplicate checks based on URL or title+company
                    if db.job_exists(job['job_id']):
                        continue
                    
                    logger.info(f"Analyzing Job Opportunity: {job['title']} at {job['company']}")
                    
                    job_embedding = analyzer.get_embedding(job['title'] + " " + job['description'])
                    
                    match_analysis = {}
                    if profile:
                        # Deep LLM analysis
                        match_analysis = analyzer.analyze_job_semantic(
                            profile=profile,
                            job_title=job['title'],
                            job_description=job['description'],
                            target_seniority=exp_level,
                            target_job_type=job_type
                        )
                        # Vector cosine similarity
                        vector_sim = calculate_cosine_similarity(job_embedding, profile.get('embedding', []))
                        
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
                    
                    # 5. Save details and match to database
                    db.add_job(job, job_embedding)
                    db.save_match(match_analysis)
                    
                    # 6. Trigger notification if Match Score >= 80
                    if match_analysis.get('matchScore', 0) >= 80:
                        email_client.send_notification(job, match_analysis)

                    # 7. Broadcast new job discovery to connected clients
                    if broadcast_callback:
                        broadcast_data = {**job, **match_analysis}
                        await broadcast_callback({"type": "new_job", "data": broadcast_data})
                        
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
