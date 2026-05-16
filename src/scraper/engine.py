import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from src.core.config import config
from src.core.logger import logger

class JobScraper:
    def __init__(self):
        self.keywords = [k.strip() for k in config.JOB_KEYWORDS.split(",")]
        self.locations = [l.strip() for l in config.JOB_LOCATIONS.split(",")]

    async def _get_browser(self, p):
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
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
                    # f_TPR=r86400 is "Past 24 hours", sortBy=DD is "Most Recent"
                    url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_TPR=r86400&sortBy=DD"
                    logger.info(f"Scraping LinkedIn: {url}")
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=60000)
                        await asyncio.sleep(random.uniform(3, 7))
                        
                        # Extract job cards
                        job_cards = await page.query_selector_all(".base-card")
                        logger.info(f"Found {len(job_cards)} potential job cards")
                        
                        for card in job_cards[:10]: # Increased to top 10 for more variety
                            try:
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
                                        # Fetch JD in a new context to avoid session pollution
                                        jd_context = await browser.new_context()
                                        jd_p = await jd_context.new_page()
                                        await stealth_async(jd_p)
                                        await jd_p.goto(link, wait_until='networkidle', timeout=60000)
                                        await asyncio.sleep(random.uniform(1, 3))
                                        
                                        jd_elem = await jd_p.query_selector(".description__text")
                                        jd_text = await jd_elem.inner_text() if jd_elem else ""
                                        await jd_context.close()

                                        jobs.append({
                                            "job_id": job_id,
                                            "title": title.strip(),
                                            "company": company.strip(),
                                            "url": link,
                                            "description": jd_text.strip()
                                        })
                                        logger.info(f"Captured: {title.strip()} @ {company.strip()}")
                            except Exception as card_err:
                                logger.warning(f"Failed to parse card: {card_err}")
                                continue
                                
                    except Exception as e:
                        logger.error(f"Error scraping LinkedIn for {keyword}: {e}")
            
            await browser.close()
        return jobs
