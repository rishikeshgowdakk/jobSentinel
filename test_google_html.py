import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        await stealth_async(page)
        
        url = 'https://www.google.com/search?q=site:boards.greenhouse.io+OR+site:jobs.lever.co+"Software+Engineer"+"Remote"&tbs=qdr:w'
        print(f"Fetching: {url}")
        await page.goto(url, wait_until='load', timeout=60000)
        await asyncio.sleep(3)
        html = await page.content()
        with open("google_debug.html", "w") as f:
            f.write(html)
        print(f"Saved {len(html)} bytes to google_debug.html")
        await browser.close()

asyncio.run(run())
