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
        headless = getattr(config, 'SCRAPE_HEADLESS', False)
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")
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
                        await page.goto(url, wait_until='load', timeout=60000)
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
                                    
                                    loc_elem = await card.query_selector(".job-search-card__location")
                                    if not loc_elem:
                                        loc_elem = await card.query_selector(".base-search-card__metadata")
                                    loc_text = await loc_elem.inner_text() if loc_elem else "Remote"
                                    
                                    link_elem = await card.query_selector(".base-card__full-link")
                                    link = await link_elem.get_attribute("href") if link_elem else ""
                                    
                                    if link:
                                        jd_context = await browser.new_context()
                                        jd_p = await jd_context.new_page()
                                        await stealth_async(jd_p)
                                        await jd_p.goto(link, wait_until='load', timeout=60000)
                                        jd_elem = await jd_p.query_selector(".description__text")
                                        jd_text = await jd_elem.inner_text() if jd_elem else ""
                                        await jd_context.close()

                                        jobs.append({
                                            "job_id": job_id,
                                            "title": title.strip(),
                                            "company": company.strip(),
                                            "url": link,
                                            "description": jd_text.strip(),
                                            "location": loc_text.strip(),
                                            "skills": "",
                                            "source": "LinkedIn"
                                        })
                            except Exception: continue
                    except Exception as e:
                        logger.error(f"LinkedIn error: {e}")
            await browser.close()
        return jobs

    async def scrape_naukri(self, keywords=None, locations=None, job_type="All", experience_level="All"):
        jobs = []
        search_keywords = keywords if keywords else self.keywords
        search_locations = locations if locations else self.locations
        
        async with async_playwright() as p:
            browser, page = await self._get_browser(p)
            for keyword in search_keywords:
                for location in search_locations:
                    k_slug = keyword.lower().replace(" ", "-")
                    l_slug = location.lower().replace(" ", "-")
                    
                    # Search URL with jobAge=1 for the last 24 hours
                    url = f"https://www.naukri.com/{k_slug}-jobs-in-{l_slug}?jobAge=1"
                    logger.info(f"Naukri [{keyword} | {location}]: Searching...")
                    
                    try:
                        await page.goto(url, wait_until='load', timeout=60000)
                        await asyncio.sleep(random.uniform(3, 5))
                        
                        job_cards = await page.query_selector_all(".srp-jobtuple-wrapper")
                        logger.info(f"Naukri: Found {len(job_cards)} job cards on page.")
                        
                        for card in job_cards[:8]:
                            try:
                                title_elem = await card.query_selector("a.title")
                                if not title_elem:
                                    continue
                                    
                                title = await title_elem.inner_text()
                                link = await title_elem.get_attribute("href")
                                
                                comp_elem = await card.query_selector("a.comp-name")
                                company = await comp_elem.inner_text() if comp_elem else "N/A"
                                
                                loc_elem = await card.query_selector(".loc-wrap")
                                if not loc_elem:
                                    loc_elem = await card.query_selector(".location")
                                if not loc_elem:
                                    loc_elem = await card.query_selector(".locWdth")
                                loc_text = await loc_elem.inner_text() if loc_elem else "N/A"
                                
                                exp_elem = await card.query_selector(".exp-wrap")
                                if not exp_elem:
                                    exp_elem = await card.query_selector(".experience")
                                if not exp_elem:
                                    exp_elem = await card.query_selector(".expwdth")
                                exp_text = await exp_elem.inner_text() if exp_elem else "N/A"
                                
                                # Skills
                                skills_elems = await card.query_selector_all(".tag-li, .tags-gt li, .skill-tag, .chip")
                                skills_list = [await s.inner_text() for s in skills_elems]
                                skills = ", ".join(skills_list) if skills_list else ""
                                
                                # Snippet/Description
                                desc_elem = await card.query_selector(".job-desc, .jobDescription, .desc")
                                description = await desc_elem.inner_text() if desc_elem else ""
                                
                                job_id = "nk_" + str(hash(title + company + link))[-8:]
                                
                                jobs.append({
                                    "job_id": job_id,
                                    "title": title.strip(),
                                    "company": company.strip(),
                                    "url": link,
                                    "description": description.strip(),
                                    "skills": skills,
                                    "location": loc_text.strip(),
                                    "experience": exp_text.strip(),
                                    "source": "Naukri"
                                })
                            except Exception as card_e:
                                logger.error(f"Error parsing Naukri card: {card_e}")
                                continue
                    except Exception as e:
                        logger.error(f"Naukri error: {e}")
            await browser.close()
        return jobs
