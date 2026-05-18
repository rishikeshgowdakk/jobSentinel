import asyncio
import os
import time
from src.core.config import config
from src.core.logger import logger
from src.core.db import db
from src.scraper.engine import JobScraper
from src.intelligence.gemini import GeminiAnalyzer
from src.generator.resume import ResumeGenerator
from src.notify.email_client import EmailClient
from src.notify.calendar import CalendarClient
from src.notify.github import GithubClient

async def run_scanner(broadcast_callback=None):
    logger.info("Initializing JobSentinel Scanner Loop...")
    
    scraper = JobScraper()
    analyzer = GeminiAnalyzer()
    generator = ResumeGenerator()
    email_client = EmailClient()
    github_client = GithubClient()
    
    calendar_client = None
    try:
        calendar_client = CalendarClient()
    except Exception:
        logger.warning("Google Calendar not configured.")

    while True:
        try:
            if not os.path.exists(config.MASTER_RESUME_PATH):
                logger.error("Master resume missing. Please upload one via the dashboard.")
                await asyncio.sleep(10)
                continue

            with open(config.MASTER_RESUME_PATH, 'r') as f:
                master_resume = f.read()

            logger.info("Extracting profile from resume...")
            resume_params = analyzer.extract_resume_parameters(master_resume)

            # Get user preferences
            db_keywords = db.get_setting("keywords")
            db_locations = db.get_setting("locations")
            job_type = db.get_setting("job_type", "All")
            exp_level = db.get_setting("experience_level", "All")
            
            keywords = [k.strip() for k in db_keywords.split(",")] if db_keywords else resume_params.get('tech_stack', ['Software Engineer'])[:2]
            locations = [l.strip() for l in db_locations.split(",")] if db_locations else [resume_params.get('location', 'Remote')]

            logger.info(f"HUNT START: {keywords} in {locations} ({job_type})")

            # Scrape platforms in parallel
            tasks = [
                scraper.scrape_linkedin(keywords, locations, job_type, exp_level),
                scraper.scrape_google_jobs(keywords, locations, job_type, exp_level)
            ]
            
            platform_results = await asyncio.gather(*tasks)
            all_found_jobs = [j for platform in platform_results for j in platform]

            for job in all_found_jobs:
                if db.job_exists(job['job_id']):
                    continue
                
                logger.info(f"Analyzing {job['title']} at {job['company']}...")
                analysis = analyzer.analyze_job(
                    master_resume, 
                    job['description'],
                    user_yoe=resume_params.get('yoe', 0),
                    user_tech_stack=resume_params.get('tech_stack', []),
                    target_seniority=exp_level,
                    target_job_type=job_type
                )
                
                job['ats_score'] = analysis.get('ats_score', 0) if analysis else 0
                job['rejection_reason'] = analysis.get('rejection_reason') if analysis else None
                job['status'] = 'tailored' if job['ats_score'] >= 80 else 'ignored'
                
                if job['status'] == 'tailored':
                    logger.info(f"MATCH FOUND ({job['ats_score']}%): Generating tailored resume...")
                    resume_path = generator.generate_pdf(analysis, job['job_id'])
                    if resume_path:
                        email_client.send_notification(job['title'], job['company'], job['url'], resume_path)
                        if calendar_client: calendar_client.create_event(job['title'], job['company'])
                        github_client.push_changes(job['title'], job['company'])
                
                # Save and BROADCAST immediately
                db.add_job(job)
                if broadcast_callback:
                    await broadcast_callback({"type": "new_job", "data": job})

            logger.info(f"Hunt cycle complete. Sleeping {config.SCRAPE_INTERVAL}s...")
            await asyncio.sleep(config.SCRAPE_INTERVAL)
            
        except Exception as e:
            logger.error(f"Scanner Loop Error: {e}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(run_scanner())
