"""
scrapers/universities/malvern_house_spider.py
───────────────────────────────────
Spider for Malvern House International.
URL: https://malvernhouse.com/courses/

NOTE: Uses Playwright to bypass potential Cloudflare human verification.
"""

from scrapers.base_spider import BaseUniversitySpider


from scrapy_playwright.page import PageMethod

class MalvernHouseSpider(BaseUniversitySpider):
    name = "malvern_house"
    university_name = "Malvern House International"
    university_location = "London, England"
    
    # Enabling Playwright for human verification challenges
    needs_js = True

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 5,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ],
        },
        "PLAYWRIGHT_CONTEXT_ARGS": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    }

    start_urls = [
        "https://malvernhouse.com/our-courses/",
    ]

    def start_requests(self):
        for url in self.start_urls:
            req = self._make_request(url, callback=self.parse_course_list, use_js=True)
            req.meta["playwright_page_methods"] = [
                PageMethod("wait_for_function", "document.title !== 'Just a moment...'"),
                PageMethod("wait_for_selector", "footer", timeout=30000),
            ]
            yield req

    def parse_course_list(self, response):
        links = response.css(".course-card a::attr(href), h2.entry-title a::attr(href), a::attr(href)").getall()
        # Add basic links that contain "course" but are not media
        valid_links = [l for l in links if "course" in l and not l.endswith(".jpg")]
        self.logger.info(f"[Malvern House] Found {len(valid_links)} links on {response.url}")

        for href in set(valid_links):
            if "our-courses" not in href:
                continue
            req = self._make_request(response.urljoin(href), callback=self.parse_course, use_js=True)
            req.meta["playwright_page_methods"] = [
                PageMethod("wait_for_function", "document.title !== 'Just a moment...'"),
                PageMethod("wait_for_selector", "footer", timeout=30000),
            ]
            yield req

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
