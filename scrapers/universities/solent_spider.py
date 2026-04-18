"""
scrapers/universities/solent_spider.py
───────────────────────────────────────
Spider for Solent University.
URL: https://www.solent.ac.uk/courses
"""

from scrapers.base_spider import BaseUniversitySpider


class SolentSpider(BaseUniversitySpider):
    name = "solent"
    university_name = "Solent University"
    university_location = "Southampton, England"
    needs_js = False

    start_urls = [
        "https://www.solent.ac.uk/courses",
    ]

    course_link_selector = "h2 a[href^='/courses/undergraduate/']"
    next_page_selector   = "nav.pagination a[aria-label='Next page']"

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Solent] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
