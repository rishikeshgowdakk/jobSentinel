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

    async def scrape_linkedin(self, keywords=None, locations=None, job_type="All", experience_level="All"):
        jobs = []
        search_keywords = keywords if keywords else self.keywords
        search_locations = locations if locations else self.locations
        
        async with async_playwright() as p:
            browser, page = await self._get_browser(p)
            for keyword in search_keywords:
                for location in search_locations:
                    # LinkedIn Params: f_JT (F=Full, P=Part, I=Internship), f_E (1=Intern, 2=Entry, 4=Mid)
                    url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_TPR=r86400&sortBy=DD"
                    
                    if job_type in ["F", "P", "I"]: 
                        url += f"&f_JT={job_type}"
                    
                    # If user chose Fresher (2), we also search for Internship (1) on LinkedIn
                    if experience_level == "2":
                        url += "&f_E=1,2"
                    elif experience_level == "4":
                        url += "&f_E=4"
                        
                    logger.info(f"LinkedIn [{keyword} | {location}]: Searching...")
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=60000)
                        await asyncio.sleep(random.uniform(2, 4))
                        
                        job_cards = await page.query_selector_all(".base-card")
                        for card in job_cards[:8]:
                            try:
                                job_id = await card.get_attribute("data-entity-urn")
                                if job_id:
                                    job_id = "li_" + job_id.split(":")[-1]
                                    
                                    title_elem = await card.query_selector(".base-search-card__title")
                                    title = await title_elem.inner_text() if title_elem else "N/A"
                                    
                                    company_elem = await card.query_selector(".base-search-card__subtitle")
                                    company = await company_elem.inner_text() if company_elem else "N/A"
                                    
                                    link_elem = await card.query_selector(".base-card__full-link")
                                    link = await link_elem.get_attribute("href") if link_elem else ""
                                    
                                    if link:
                                        jd_context = await browser.new_context()
                                        jd_p = await jd_context.new_page()
                                        await stealth_async(jd_p)
                                        await jd_p.goto(link, wait_until='networkidle', timeout=60000)
                                        jd_elem = await jd_p.query_selector(".description__text")
                                        jd_text = await jd_elem.inner_text() if jd_elem else ""
                                        await jd_context.close()

                                        jobs.append({
                                            "job_id": job_id,
                                            "title": title.strip(),
                                            "company": company.strip(),
                                            "url": link,
                                            "description": jd_text.strip(),
                                            "source": "LinkedIn"
                                        })
                            except Exception: continue
                    except Exception as e:
                        logger.error(f"LinkedIn error: {e}")
            await browser.close()
        return jobs

    async def scrape_google_jobs(self, keywords=None, locations=None, job_type="All", experience_level="All"):
        jobs = []
        search_keywords = keywords if keywords else self.keywords
        search_locations = locations if locations else self.locations
        
        async with async_playwright() as p:
            browser, page = await self._get_browser(p)
            for keyword in search_keywords:
                for location in search_locations:
                    query = f"{keyword} jobs in {location}"
                    
                    if job_type == "F": query += " full-time"
                    elif job_type == "P": query += " part-time"
                    elif job_type == "I": query += " internship"
                    
                    if experience_level == "2": query += " entry level fresher"
                    elif experience_level == "4": query += " experienced mid-senior"
                    
                    url = f"https://www.google.com/search?q={query.replace(' ', '+')}&ibp=htl;jobs"
                    logger.info(f"Google Jobs [{keyword} | {location}]: Searching...")
                    
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=60000)
                        await asyncio.sleep(random.uniform(3, 5))
                        
                        job_cards = await page.query_selector_all("li[role='listitem']")
                        for card in job_cards[:8]:
                            try:
                                title_elem = await card.query_selector("div[role='heading']")
                                title = await title_elem.inner_text() if title_elem else "N/A"
                                
                                details = await card.query_selector_all("div > div > div")
                                company = await details[1].inner_text() if len(details) > 1 else "N/A"
                                
                                # Click to get JD
                                await card.click()
                                await asyncio.sleep(1)
                                
                                jd_elem = await page.query_selector(".YbeU7") 
                                jd_text = await jd_elem.inner_text() if jd_elem else ""
                                
                                job_id = "gj_" + str(hash(title + company))[-8:]
                                
                                jobs.append({
                                    "job_id": job_id,
                                    "title": title.strip(),
                                    "company": company.strip(),
                                    "url": url, 
                                    "description": jd_text.strip(),
                                    "source": "Google Jobs"
                                })
                            except Exception: continue
                    except Exception as e:
                        logger.error(f"Google Jobs error: {e}")
            await browser.close()
        return jobs
