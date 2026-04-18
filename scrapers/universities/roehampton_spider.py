"""
scrapers/universities/roehampton_spider.py
────────────────────────────────────────────
Spider for Roehampton University.
URL: https://www.roehampton.ac.uk/study/undergraduate-courses/
"""

from scrapers.base_spider import BaseUniversitySpider


class RoehamptonSpider(BaseUniversitySpider):
    name = "roehampton"
    university_name = "Roehampton University"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.roehampton.ac.uk/study/undergraduate-courses/",
    ]

    course_link_selector = "a[href^='/study/undergraduate-courses/']"
    next_page_selector   = None  # Single page listing

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Roehampton] Found {len(links)} links on {response.url}")

        for href in links:
            # Filter out the listing page itself
            if href != "/study/undergraduate-courses/":
                yield self._make_request(response.urljoin(href), callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
