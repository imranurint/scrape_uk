import asyncio
from playwright.async_api import async_playwright

async def get_page(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        content = await page.content()
        await browser.close()
        return content

content = asyncio.run(get_page("https://malvernhouse.com/page-sitemap.xml"))
with open("page_sitemap.xml", "w") as f:
    f.write(content)

