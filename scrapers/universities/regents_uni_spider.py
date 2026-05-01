"""
scrapers/universities/regents_uni_spider.py
───────────────────────────────────
Spider for Regent's University London.
"""

from scrapy import Request
from scrapers.base_spider import BaseUniversitySpider
# from scrapy_playwright.page import PageMethod # No longer needed if using impersonate

class RegentsUniSpider(BaseUniversitySpider):
    name = "regents_uni"
    university_name = "Regent's University London"
    university_location = "London, England"
    
    # Disable Playwright if using impersonate
    needs_js = False 

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy_impersonate.ImpersonateMiddleware": 100,
        },
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 5,
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

    def _make_request(self, url, callback, **kwargs):
        return Request(
            url=url,
            callback=callback,
            meta={"impersonate": "chrome120"}, # This mimics Chrome exactly
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
