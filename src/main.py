import asyncio
import os
import time
from src.core.config import config
from src.core.logger import logger
from src.core.db import db
from src.scraper.engine import JobScraper
from src.intelligence.gemini import GeminiAnalyzer

async def run_scanner(broadcast_callback=None):
    logger.info("Initializing JobSentinel Scanner Loop (No Resume Mode)...")
    
    scraper = JobScraper()
    analyzer = GeminiAnalyzer()
    
    while True:
        try:
            # Get user preferences
            db_keywords = db.get_setting("keywords")
            db_locations = db.get_setting("locations")
            job_type = db.get_setting("job_type", "All")
            exp_level = db.get_setting("experience_level", "All")
            
            keywords = [k.strip() for k in db_keywords.split(",")] if db_keywords else [config.JOB_KEYWORDS]
            locations = [l.strip() for l in db_locations.split(",")] if db_locations else [config.JOB_LOCATIONS]

            logger.info(f"HUNT START: Keywords={keywords} | Locations={locations} | Type={job_type} | Exp={exp_level}")

            # Scrape platforms in parallel
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
                    logger.error(f"Scraper task encountered error: {res}")

            logger.info(f"Scrape phase done. Found {len(all_found_jobs)} jobs. Commencing analysis...")

            for job in all_found_jobs:
                if db.job_exists(job['job_id']):
                    continue
                
                logger.info(f"New job: {job['title']} at {job['company']} ({job['source']}). Analyzing...")
                
                # Analyze using updated analyzer without resume
                analysis = analyzer.analyze_job(
                    job_title=job['title'],
                    job_description=job['description'],
                    target_seniority=exp_level,
                    target_job_type=job_type
                )
                
                job['summary'] = analysis.get('summary', job['description'][:150] + "...")
                
                # If skills were extracted by analyzer, combine them with scraped skills
                analyzer_skills = analysis.get('skills', [])
                scraped_skills = [s.strip() for s in job.get('skills', '').split(",")] if job.get('skills') else []
                combined_skills = list(set(scraped_skills + analyzer_skills))
                job['skills'] = ", ".join(combined_skills[:8])  # Keep top 8 skills
                
                is_match = analysis.get('is_match', True)
                job['status'] = 'matched' if is_match else 'ignored'
                job['rejection_reason'] = analysis.get('match_reason') if not is_match else None
                
                # Save to Database
                db.add_job(job)
                
                # Broadcast immediately
                if broadcast_callback:
                    await broadcast_callback({"type": "new_job", "data": job})

            logger.info(f"Hunt cycle complete. Sleeping {config.SCRAPE_INTERVAL}s...")
            await asyncio.sleep(config.SCRAPE_INTERVAL)
            
        except Exception as e:
            logger.error(f"Scanner Loop Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(run_scanner())
