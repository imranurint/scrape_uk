import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://search.brookes.ac.uk/s/search.html?collection=oxford-brookes~sp-course-finder&f.Study+level%7CcourseLevel=undergraduate&query=")
        await page.wait_for_timeout(5000)
        await page.screenshot(path="brookes.png", full_page=True)
        content = await page.content()
        with open("brookes.html", "w") as f:
            f.write(content)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
