"""
scrapers/universities/richmond_spider.py
───────────────────────────────────
Spider for Richmond American University London.
URL: https://www.richmond.ac.uk/undergraduate-programmes/
"""

from scrapers.base_spider import BaseUniversitySpider


class RichmondSpider(BaseUniversitySpider):
    name = "richmond"
    university_name = "Richmond American University London"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.richmond.ac.uk/undergraduate-programmes/",
    ]

    course_link_selector = "a.programme-title"
    next_page_selector   = None

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Richmond] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
