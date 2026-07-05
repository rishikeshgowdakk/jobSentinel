import asyncio
from src.scraper.engine import JobScraper

async def run():
    scraper = JobScraper()
    print("Scraping LinkedIn for test...")
    jobs = await scraper.scrape_linkedin(keywords=["Python"], locations=["Remote"])
    print(f"Found {len(jobs)} jobs")
    if jobs:
        print("Example:", jobs[0]['title'], "-", jobs[0]['company'])

asyncio.run(run())
