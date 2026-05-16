import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from src.core.config import config
from src.core.logger import logger

class JobScraper:
    def __init__(self):
        self.keywords = config.JOB_KEYWORDS.split(",")
        self.locations = config.JOB_LOCATIONS.split(",")

    async def _get_browser(self, p):
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await stealth_async(page)
        return browser, page

    async def scrape_linkedin(self):
        jobs = []
        async with async_playwright() as p:
            browser, page = await self._get_browser(p)
            for keyword in self.keywords:
                for location in self.locations:
                    url = f"https://www.linkedin.com/jobs/search/?keywords={keyword.strip()}&location={location.strip()}&f_TPR=r86400&sortBy=DD"
                    logger.info(f"Scraping LinkedIn: {url}")
                    try:
                        await page.goto(url, wait_until='networkidle')
                        await asyncio.sleep(random.uniform(2, 5))
                        
                        # Extract job cards
                        job_cards = await page.query_selector_all(".base-card")
                        for card in job_cards[:5]: # Take top 5 for latency
                            job_id = await card.get_attribute("data-entity-urn")
                            if job_id:
                                job_id = job_id.split(":")[-1]
                                title_elem = await card.query_selector(".base-search-card__title")
                                title = await title_elem.inner_text() if title_elem else "N/A"
                                
                                company_elem = await card.query_selector(".base-search-card__subtitle")
                                company = await company_elem.inner_text() if company_elem else "N/A"
                                
                                link_elem = await card.query_selector(".base-card__full-link")
                                link = await link_elem.get_attribute("href") if link_elem else ""
                                
                                if link:
                                    # Fetch JD
                                    jd_page_context = await browser.new_context()
                                    jd_p = await jd_page_context.new_page()
                                    await stealth_async(jd_p)
                                    await jd_p.goto(link, wait_until='networkidle')
                                    jd_elem = await jd_p.query_selector(".description__text")
                                    jd_text = await jd_elem.inner_text() if jd_elem else ""
                                    await jd_page_context.close()

                                    jobs.append({
                                        "job_id": job_id,
                                        "title": title.strip(),
                                        "company": company.strip(),
                                        "url": link,
                                        "description": jd_text.strip()
                                    })
                                    logger.info(f"Found Job: {title.strip()} at {company.strip()}")
                    except Exception as e:
                        logger.error(f"Error scraping LinkedIn for {keyword}: {e}")
            
            await browser.close()
        return jobs
