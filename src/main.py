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

async def run_scanner():
    logger.info("Starting Sentinel-Apply Background Scanner...")
    
    scraper = JobScraper()
    analyzer = GeminiAnalyzer()
    generator = ResumeGenerator()
    email_client = EmailClient()
    github_client = GithubClient()
    
    # Optional: Calendar client requires manual auth first time
    calendar_client = None
    try:
        calendar_client = CalendarClient()
    except Exception as e:
        logger.warning(f"Calendar initialization failed (likely missing credentials): {e}")

    while True:
        try:
            # Re-read master resume every loop in case it was updated via API
            if not os.path.exists(config.MASTER_RESUME_PATH):
                logger.error(f"Master resume not found at {config.MASTER_RESUME_PATH}. Creating a dummy one.")
                with open(config.MASTER_RESUME_PATH, 'w') as f:
                    f.write("# Master Resume\nExperience at Tech Corp...")

            with open(config.MASTER_RESUME_PATH, 'r') as f:
                master_resume = f.read()

            logger.info("Extracting search parameters from master resume...")
            resume_params = analyzer.extract_resume_parameters(master_resume)
            logger.info(f"Targeting: {resume_params.get('location')} | YOE: {resume_params.get('yoe')} | Tech: {resume_params.get('tech_stack')}")

            logger.info("Scanning for new jobs...")
            # Use user-defined preferences if set, otherwise fallback to extracted resume params
            db_keywords = db.get_setting("keywords")
            db_locations = db.get_setting("locations")
            job_type = db.get_setting("job_type", "All")
            experience_level = db.get_setting("experience_level", "All")
            
            if db_keywords:
                keywords = [k.strip() for k in db_keywords.split(",")]
            else:
                keywords = resume_params.get('tech_stack', ['Software Engineer'])[:2]
                
            if db_locations:
                locations = [l.strip() for l in db_locations.split(",")]
            else:
                locations = [resume_params.get('location', 'Remote')]
            
            logger.info(f"Using search parameters: Keywords: {keywords} | Locations: {locations} | Job Type: {job_type} | Exp: {experience_level}")
            
            new_jobs = await scraper.scrape_linkedin(
                keywords=keywords, 
                locations=locations,
                job_type=job_type,
                experience_level=experience_level
            )
            
            for job in new_jobs:
                if db.job_exists(job['job_id']):
                    continue
                
                logger.info(f"Analyzing new job: {job['title']} at {job['company']}")
                analysis = analyzer.analyze_job(
                    master_resume, 
                    job['description'],
                    user_yoe=resume_params.get('yoe', 0),
                    user_tech_stack=resume_params.get('tech_stack', [])
                )
                
                if analysis and analysis.get('ats_score', 0) >= 80:
                    logger.info(f"High match found! ATS Score: {analysis['ats_score']}")
                    
                    # Generate tailored resume
                    resume_path = generator.generate_pdf(analysis, job['job_id'])
                    
                    if resume_path:
                        # Notify
                        email_client.send_notification(
                            job['title'], 
                            job['company'], 
                            job['url'], 
                            resume_path
                        )
                        
                        if calendar_client:
                            calendar_client.create_event(job['title'], job['company'])
                        
                        # Save to DB
                        job['ats_score'] = analysis['ats_score']
                        job['status'] = 'tailored'
                        db.add_job(job)
                        
                        # Push results to GitHub
                        github_client.push_changes(job['title'], job['company'])
                    else:
                        logger.error("Failed to generate tailored resume.")
                else:
                    logger.info(f"Low match or analysis failed for {job['title']}")
                    # Still add to DB to avoid re-processing
                    job['ats_score'] = analysis.get('ats_score', 0) if analysis else 0
                    job['status'] = 'ignored'
                    db.add_job(job)

            logger.info(f"Scan complete. Sleeping for {config.SCRAPE_INTERVAL} seconds...")
            await asyncio.sleep(config.SCRAPE_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(60) # Sleep before retrying

if __name__ == "__main__":
    asyncio.run(run_scanner())
