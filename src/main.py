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

async def main():
    logger.info("Starting Sentinel-Apply...")
    
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

    # Load master resume
    if not os.path.exists(config.MASTER_RESUME_PATH):
        logger.error(f"Master resume not found at {config.MASTER_RESUME_PATH}. Creating a dummy one.")
        with open(config.MASTER_RESUME_PATH, 'w') as f:
            f.write("# Master Resume\nExperience at Tech Corp...")

    with open(config.MASTER_RESUME_PATH, 'r') as f:
        master_resume = f.read()

    while True:
        try:
            logger.info("Scanning for new jobs...")
            new_jobs = await scraper.scrape_linkedin()
            
            for job in new_jobs:
                if db.job_exists(job['job_id']):
                    continue
                
                logger.info(f"Analyzing new job: {job['title']} at {job['company']}")
                analysis = analyzer.analyze_job(master_resume, job['description'])
                
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
    asyncio.run(main())
