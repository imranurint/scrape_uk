"""
scrapers/universities/regents_uni_spider.py
───────────────────────────────────
Spider for Regent's University London.
"""

from scrapers.base_spider import BaseUniversitySpider
from scrapy_playwright.page import PageMethod


class RegentsUniSpider(BaseUniversitySpider):
    name = "regents_uni"
    university_name = "Regent's University London"
    university_location = "London, England"
    
    # Enabling Playwright
    needs_js = True

    custom_settings = {
        "CONCURRENT_REQUESTS": 2,
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 1,
        "DOWNLOAD_DELAY": 4,
        # Stealth settings
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": False, # Change this to False
            "args": ["--disable-blink-features=AutomationControlled"],
        },
    }

    start_urls = [
        "https://www.regents.ac.uk/undergraduate",
        "https://www.regents.ac.uk/postgraduate",
        "https://www.regents.ac.uk/foundation",
        "https://www.regents.ac.uk/english/courses",
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield self._make_request(
                url, 
                callback=self.parse_course_list,
                use_js=True
            )

    def _make_request(self, url, callback, use_js=None, cb_kwargs=None, referer=None):
        if use_js is None:
            use_js = self.needs_js

        meta = {
            "playwright": True,
            "playwright_include_page": False,
            "playwright_context_args": {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "locale": "en-GB",
                "viewport": {"width": 1920, "height": 1080},
            }
        } if use_js else {}
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }
        if referer:
            headers["Referer"] = referer

        if use_js:
            if url in self.start_urls:
                meta["playwright_page_methods"] = [
                    PageMethod("wait_for_load_state", "networkidle"),
                    PageMethod("wait_for_timeout", 3000),
                ]
            else:
                meta["playwright_page_methods"] = [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                    PageMethod("wait_for_timeout", 2000),
                ]

        from scrapy import Request
        return Request(
            url=url,
            callback=callback,
            meta=meta,
            headers=headers,
            cb_kwargs=cb_kwargs or {},
            errback=self._errback,
            dont_filter=True if url in self.start_urls else False
        )

    def parse_course_list(self, response):
        if response.status == 403:
            self.logger.error(f"Blocked by CDN on listing: {response.url}")
            return

        links = response.css("main a::attr(href)").getall()
        patterns = ["/undergraduate/", "/postgraduate/", "/foundation/", "/english/courses/"]
        
        seen = set()
        count = 0
        for href in links:
            abs_url = response.urljoin(href).split('#')[0].rstrip('/')
            if any(p in abs_url for p in patterns) and abs_url not in [u.rstrip('/') for u in self.start_urls]:
                if abs_url not in seen:
                    seen.add(abs_url)
                    count += 1
                    # Pass the current listing page as Referer
                    yield self._make_request(abs_url, callback=self.parse_course, referer=response.url)
        
        self.logger.info(f"[Regent's Uni] Found {count} unique course links on {response.url}")

    def parse_course(self, response):
        if response.status == 403:
            self.logger.warning(f"Blocked on detail page: {response.url}")
            # Optional: Fallback to non-JS request if blocked with Playwright
            return

        item = self._extract_and_normalise(response)
        if item:
            yield item
