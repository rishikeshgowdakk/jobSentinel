import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        await stealth_async(page)
        
        # d gets results from past day, w gets past week, m gets past month
        url = 'https://html.duckduckgo.com/html/?q=site:boards.greenhouse.io+OR+site:jobs.lever.co+"Software+Engineer"+"Remote"&df=w'
        print(f"Fetching: {url}")
        await page.goto(url, wait_until='load', timeout=60000)
        await asyncio.sleep(2)
        
        results = await page.query_selector_all("div.result")
        print(f"Found {len(results)} results")
        for res in results[:3]:
            a_tag = await res.query_selector("a.result__url")
            link = await a_tag.get_attribute("href") if a_tag else ""
            title_tag = await res.query_selector("h2.result__title")
            title = await title_tag.inner_text() if title_tag else ""
            print(f"- {title.strip()} ({link})")
            
        await browser.close()

asyncio.run(run())
