"""
scrapers/universities/royal_holloway_isc_spider.py
────────────────────────────────────────────────────
Spider for Royal Holloway International Study Centre (Study Group).
URL: https://www.rhulisc.com/programmes
"""

from scrapers.base_spider import BaseUniversitySpider


class RoyalHollowayISCSpider(BaseUniversitySpider):
    name = "royal_holloway_isc"
    university_name = "Royal Holloway ISC (Study Group)"
    university_location = "Egham, England"
    needs_js = False

    start_urls = [
        "https://www.rhulisc.com/programmes",
    ]

    course_link_selector = "a[href^='/programmes/']"
    next_page_selector   = None

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[RHUL ISC] Found {len(links)} links on {response.url}")

        for href in links:
            if href != "/programmes":
                yield self._make_request(response.urljoin(href), callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
