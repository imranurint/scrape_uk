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
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 8,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 3.0,
        "AUTOTHROTTLE_MAX_DELAY": 60,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "COOKIES_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [403, 429, 500, 502, 503, 504],
    }

    start_urls = [
        "https://www.regents.ac.uk/undergraduate",
        "https://www.regents.ac.uk/postgraduate",
        "https://www.regents.ac.uk/foundation",
        "https://www.regents.ac.uk/english/courses",
        "https://www.regents.ac.uk/programme-listing/all",
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield self._make_request(
                url, 
                callback=self.parse_course_list
            )

    def _make_request(self, url, callback, referer=None):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        if referer:
            headers["Referer"] = referer

        return Request(
            url=url,
            callback=callback,
            headers=headers,
            errback=self._errback,
            dont_filter=True if url in self.start_urls else False
        )

    def parse_course_list(self, response):
        """
        Extract all course links from Regent's University London pages
        """
        if response.status == 403:
            self.logger.error(f"Blocked by CDN on listing: {response.url}")
            return

        self.logger.info(f"[Regent's Uni] Processing {response.url}")
        
        # Strategy 1: Extract ALL links first
        all_links = response.css('a::attr(href)').getall()
        self.logger.info(f"[Regent's Uni] Total links found: {len(all_links)}")
        
        # Strategy 2: Filter for course-related URLs
        course_links = []
        for link in all_links:
            if not link:
                continue
            if link.startswith(("tel:", "mailto:", "javascript:", "#")):
                continue
            
            # Regent's University course URL patterns
            if any(pattern in link for pattern in [
                '/undergraduate/',
                '/postgraduate/',
                '/foundation/',
                '/english/courses/',
                '/programme/',
                '/course/',
                'regents.ac.uk/undergraduate',
                'regents.ac.uk/postgraduate',
                'regents.ac.uk/foundation'
            ]):
                course_links.append(link)
        
        # Strategy 3: Remove duplicates and navigation
        final_links = []
        seen = set()
        for link in course_links:
            # Skip navigation/filter links
            if any(skip in link for skip in [
                '?query=',
                '?collection=',
                '?profile=',
                '?f.Level',
                'page=',
                '#',
                'undergraduate',
                'postgraduate',
                'foundation',
                'english/courses',
                'programme-listing/all'
            ]):
                continue
            
            abs_url = response.urljoin(link)
            if abs_url not in seen:
                seen.add(abs_url)
                final_links.append(abs_url)
        
        self.logger.info(f"[Regent's Uni] Found {len(final_links)} course links")
        
        # Strategy 4: Yield course detail requests
        for url in final_links:
            yield self._make_request(url, callback=self.parse_course, referer=response.url)

        # Follow pagination if present
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        if response.status == 403:
            self.logger.warning(f"Blocked on detail page: {response.url}")
            return

        item = self._extract_and_normalise(response)
        if item:
            yield item