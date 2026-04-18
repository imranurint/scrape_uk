import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled"
        ])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        # Visit index page first
        print("Visiting index...")
        await page.goto("https://malvernhouse.com/our-courses/", wait_until="networkidle")
        print("Visiting course page...")
        await page.goto("https://malvernhouse.com/our-courses/teacher-training/", wait_until="networkidle")
        html = await page.content()
        with open("test_course.html", "w") as f:
            f.write(html)
        print("Done", "cloudflare" in html.lower() or "just a moment" in html.lower())
        await browser.close()

asyncio.run(main())
