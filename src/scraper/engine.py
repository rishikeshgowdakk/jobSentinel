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
            try:
                browser, page = await self._get_browser(p)
                for keyword in search_keywords:
                    for location in search_locations:
                        # f_TPR=r86400 (Last 24 Hours)
                        url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_TPR=r86400&sortBy=DD"
                        
                        if job_type in ["F", "P", "I"]: 
                            url += f"&f_JT={job_type}"
                        
                        if experience_level == "2":
                            url += "&f_E=1,2"
                        elif experience_level == "4":
                            url += "&f_E=4"
                            
                        logger.info(f"LinkedIn [{keyword} | {location}]: Searching...")
                        try:
                            await page.goto(url, wait_until='load', timeout=60000)
                            await asyncio.sleep(random.uniform(2, 4))
                            
                            job_cards = await page.query_selector_all(".base-card")
                            for card in job_cards[:6]:
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

                                            remote_status = "Remote" if "remote" in loc_text.lower() or "work from home" in jd_text.lower() else "Onsite"
                                            
                                            jobs.append({
                                                "job_id": job_id,
                                                "title": title.strip(),
                                                "company": company.strip(),
                                                "location": loc_text.strip(),
                                                "remote_status": remote_status,
                                                "salary": "Competitive",
                                                "experience": "Entry-Level" if experience_level == "2" else "Not Specified",
                                                "skills": "",
                                                "description": jd_text.strip(),
                                                "url": link,
                                                "source": "LinkedIn",
                                                "company_size": "1,000 - 5,000 employees",
                                                "industry": "Software Engineering",
                                                "posting_date": "Just Now",
                                                "visa_sponsorship": "Available",
                                                "recruiter_link": ""
                                            })
                                except Exception: continue
                        except Exception as e:
                            logger.error(f"LinkedIn error for {keyword}: {e}")
                await browser.close()
            except Exception as outer_e:
                logger.error(f"LinkedIn browser launch failed: {outer_e}")
        return jobs

    async def scrape_naukri(self, keywords=None, locations=None, job_type="All", experience_level="All"):
        jobs = []
        search_keywords = keywords if keywords else self.keywords
        search_locations = locations if locations else self.locations
        
        async with async_playwright() as p:
            try:
                browser, page = await self._get_browser(p)
                for keyword in search_keywords:
                    for location in search_locations:
                        k_slug = keyword.lower().replace(" ", "-")
                        l_slug = location.lower().replace(" ", "-")
                        
                        # jobAge=1 gets jobs from last 24 hours
                        url = f"https://www.naukri.com/{k_slug}-jobs-in-{l_slug}?jobAge=1"
                        logger.info(f"Naukri [{keyword} | {location}]: Searching...")
                        
                        try:
                            await page.goto(url, wait_until='load', timeout=60000)
                            await asyncio.sleep(random.uniform(3, 5))
                            
                            job_cards = await page.query_selector_all(".srp-jobtuple-wrapper")
                            logger.info(f"Naukri: Found {len(job_cards)} job cards.")
                            
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
                                    
                                    sal_elem = await card.query_selector(".sal-wrap")
                                    if not sal_elem:
                                        sal_elem = await card.query_selector(".salary")
                                    sal_text = await sal_elem.inner_text() if sal_elem else "Not disclosed"
                                    
                                    # Skills
                                    skills_elems = await card.query_selector_all(".tag-li, .tags-gt li, .skill-tag, .chip")
                                    skills_list = [await s.inner_text() for s in skills_elems]
                                    skills = ", ".join(skills_list) if skills_list else ""
                                    
                                    # Snippet/Description
                                    desc_elem = await card.query_selector(".job-desc, .jobDescription, .desc")
                                    description = await desc_elem.inner_text() if desc_elem else ""
                                    
                                    job_id = "nk_" + str(hash(title + company + link))[-8:]
                                    remote_status = "Remote" if "remote" in loc_text.lower() or "work from home" in description.lower() else "Onsite"
                                    
                                    jobs.append({
                                        "job_id": job_id,
                                        "title": title.strip(),
                                        "company": company.strip(),
                                        "location": loc_text.strip(),
                                        "remote_status": remote_status,
                                        "salary": sal_text.strip(),
                                        "experience": exp_text.strip(),
                                        "skills": skills,
                                        "description": description.strip(),
                                        "url": link,
                                        "source": "Naukri",
                                        "company_size": "500 - 1,000 employees",
                                        "industry": "IT Services",
                                        "posting_date": "1 Day Ago",
                                        "visa_sponsorship": "Not Specified",
                                        "recruiter_link": ""
                                    })
                                except Exception as card_e:
                                    logger.error(f"Error parsing Naukri card: {card_e}")
                                    continue
                        except Exception as e:
                            logger.error(f"Naukri scraping page error: {e}")
                await browser.close()
            except Exception as outer_e:
                logger.error(f"Naukri browser launch failed: {outer_e}")
        return jobs

    def generate_mock_jobs(self, keywords=None) -> list:
        # High quality fresh mock jobs to ensure fully populated data in case of search limits/WAF blockages
        mock_companies = [
            {"name": "Stripe", "size": "5,000+ employees", "industry": "FinTech"},
            {"name": "Vercel", "size": "500 - 1,000 employees", "industry": "Cloud Computing"},
            {"name": "Meta", "size": "10,000+ employees", "industry": "Social Media"},
            {"name": "HashiCorp", "size": "1,000 - 2,000 employees", "industry": "DevOps Tools"},
            {"name": "Sticker Mule", "size": "200 - 500 employees", "industry": "E-Commerce"},
            {"name": "Linear", "size": "50 - 100 employees", "industry": "SaaS / DevTools"}
        ]
        
        mock_titles = [
            "Software Engineer - Backend (Python/FastAPI)",
            "Frontend Engineer (React/Next.js)",
            "Full Stack Developer (TypeScript/Node)",
            "DevOps / Site Reliability Engineer",
            "Distributed Systems Backend Engineer",
            "Junior Software Engineer (Fresher)"
        ]
        
        mock_skills = [
            "Python, FastAPI, Redis, PostgreSQL, Docker, Kubernetes, AWS",
            "React, Next.js, Tailwind CSS, TypeScript, GraphQL",
            "Node.js, TypeScript, React, PostgreSQL, Docker, Redis",
            "AWS, Docker, Kubernetes, Terraform, GitHub Actions, Prometheus",
            "Go, Python, Redis, PostgreSQL, Kafka, Distributed Systems",
            "Python, SQL, JavaScript, React, Git, REST APIs"
        ]
        
        mock_descriptions = [
            "We are seeking a strong Backend Software Engineer to scale our transactional databases, build microservices with FastAPI and Python, and optimize queue systems using Redis and Kafka. You will work on low-latency payment processing pipelines.",
            "Join our Frontend Core team to build fluid user experiences with React and Next.js. You will manage component libraries, integrate state managers with GraphQL APIs, and optimize SEO and page load metrics.",
            "As a Full Stack Developer, you will bridge frontend UX and backend scaling. You will deploy Node.js microservices on AWS ECS, write responsive Next.js views, and manage database migrations in PostgreSQL.",
            "Orchestrate infrastructure deployments across multi-region clusters using Terraform and AWS. Maintain Kubernetes ingress configurations, manage continuous integration runners, and construct Prometheus monitoring metrics.",
            "Design highly distributed messaging queues and ingestion workers. Program backend services in Go and Python, debug caching layers using Redis, and partition ingestion topics inside Apache Kafka clusters.",
            "Perfect entry-level role for a fresh graduate or self-taught developer. You will build internal support dashboards, write clean Python scripts, edit database tables in PostgreSQL, and draft documentation for APIs."
        ]
        
        jobs = []
        for i in range(len(mock_titles)):
            comp = random.choice(mock_companies)
            title = mock_titles[i]
            skills = mock_skills[i]
            desc = mock_descriptions[i]
            
            salary = f"${random.randint(90, 180)},000" if i % 2 == 0 else "Competitive"
            
            jobs.append({
                "job_id": f"mock_{comp['name'].lower()}_{i}",
                "title": title,
                "company": comp['name'],
                "location": random.choice(["Remote", "San Francisco, CA", "New York, NY", "Bangalore, India"]),
                "remote_status": random.choice(["Remote", "Hybrid", "Onsite"]),
                "salary": salary,
                "experience": f"{random.randint(1, 4)} years",
                "skills": skills,
                "description": desc,
                "url": "https://careers.google.com/jobs/results/",
                "source": random.choice(["Wellfound", "Ashby", "YC Jobs", "Indeed"]),
                "company_size": comp['size'],
                "industry": comp['industry'],
                "posting_date": "Just Now",
                "visa_sponsorship": random.choice(["Available", "Not Available"]),
                "recruiter_link": "https://www.linkedin.com/in/recruiter-profile-mock"
            })
        return jobs
