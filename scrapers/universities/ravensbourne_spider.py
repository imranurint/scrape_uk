"""
scrapers/universities/ravensbourne_spider.py
─────────────────────────────────────────────
Spider for Ravensbourne University London (Direct).
URL: https://www.ravensbourne.ac.uk/study/undergraduate/undergraduate-courses
"""

from scrapers.base_spider import BaseUniversitySpider


class RavensbourneSpider(BaseUniversitySpider):
    name = "ravensbourne"
    university_name = "Ravensbourne University London"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.ravensbourne.ac.uk/study/undergraduate/undergraduate-courses",
    ]

    course_link_selector = "a.aspect-ratio-card"
    next_page_selector   = None

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Ravensbourne] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
