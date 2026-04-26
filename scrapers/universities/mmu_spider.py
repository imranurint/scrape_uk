"""
scrapers/universities/mmu_spider.py
───────────────────────────────────
Spider for Manchester Metropolitan University (MMU).
URL: https://www.mmu.ac.uk/study/undergraduate/courses/A

MMU's old listing endpoint can redirect to a generic search page. This spider
uses the A-Z undergraduate course pages and follows detail links under
/study/undergraduate/course/.
"""

from scrapy import Request
from scrapy_playwright.page import PageMethod

from scrapers.base_spider import BaseUniversitySpider


class MMUSpider(BaseUniversitySpider):
    name = "mmu"
    university_name = "Manchester Metropolitan University"
    university_location = "Manchester, England"

    needs_js = False

    start_urls = [
        "https://www.mmu.ac.uk/study/undergraduate/courses/A",
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        },
        "PLAYWRIGHT_CONTEXT_ARGS": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
        },
    }

    def start_requests(self):
        # Establish cookies/session by visiting the homepage first
        yield Request(
            url="https://www.mmu.ac.uk/",
            callback=self.parse_homepage,
            meta={"playwright": True, "playwright_include_page": False}
        )

    def parse_homepage(self, response):
        for url in self.start_urls:
            yield self._listing_request(url, callback=self.parse_course_list)

    def _listing_request(self, url, callback):
        return Request(
            url=url,
            callback=callback,
            errback=self._errback,
            meta={
                "playwright": True,
                "playwright_include_page": False,
                "playwright_page_methods": [
                    # Wait for a basic element that Cloudflare shouldn't block.
                    PageMethod("wait_for_timeout", 15000),
                ],
            },
        )

    def parse_course_list(self, response):
        links = response.css("a[href]::attr(href)").getall()
        self.logger.info(f"[MMU] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            if not href:
                continue
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            abs_url = response.urljoin(href)
            if abs_url in seen:
                continue
            seen.add(abs_url)

            # Follow letter index pages for wider coverage.
            if "/study/undergraduate/courses/" in abs_url:
                suffix = abs_url.rstrip("/").split("/study/undergraduate/courses/")[-1]
                if len(suffix) == 1 and suffix.isalpha():
                    yield self._listing_request(abs_url, callback=self.parse_course_list)
                continue

            # Course detail pages are stable via normal Scrapy requests.
            if "/study/undergraduate/course/" in abs_url:
                yield self._make_request(abs_url, callback=self.parse_course, use_js=False)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
