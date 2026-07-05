import asyncio
from src.scraper.engine import JobScraper

async def run():
    scraper = JobScraper()
    print("Scraping DDG X-Ray for test...")
    jobs = await scraper.scrape_google_xray(keywords=["Software Engineer"], locations=["Remote"])
    print(f"Found {len(jobs)} jobs")
    for j in jobs:
        print(f" - {j['title']} @ {j['company']} ({j['source']})")

asyncio.run(run())
