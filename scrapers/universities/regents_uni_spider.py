"""
scrapers/universities/regents_uni_spider.py
───────────────────────────────────
Spider for Regent's University London.
Uses scrapy-impersonate to bypass Cloudflare/WAF.
"""

from scrapy import Request
from scrapers.base_spider import BaseUniversitySpider


class RegentsUniSpider(BaseUniversitySpider):
    name = "regents_uni"
    university_name = "Regent's University London"
    university_location = "London, England"
    
    # Disable Playwright
    needs_js = False

    custom_settings = {
        # We only need the Handler to process the 'impersonate' meta key
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_impersonate.ImpersonateDownloadHandler",
            "https": "scrapy_impersonate.ImpersonateDownloadHandler",
        },
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 5,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,
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
                callback=self.parse_course_list
            )

    def _make_request(self, url, callback, referer=None):
        meta = {
            "impersonate": "chrome120", # Handler detects this and mimics Chrome
        }
        
        headers = {}
        if referer:
            headers["Referer"] = referer

        return Request(
            url=url,
            callback=callback,
            meta=meta,
            headers=headers,
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
                    yield self._make_request(abs_url, callback=self.parse_course, referer=response.url)
        
        self.logger.info(f"[Regent's Uni] Found {count} unique course links on {response.url}")

    def parse_course(self, response):
        if response.status == 403:
            self.logger.warning(f"Blocked on detail page: {response.url}")
            return

        item = self._extract_and_normalise(response)
        if item:
            yield item