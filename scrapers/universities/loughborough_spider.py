"""
scrapers/universities/loughborough_spider.py
───────────────────────────────────
Spider for Loughborough University.
URL: https://www.lboro.ac.uk/study/undergraduate/courses/
"""

from scrapers.base_spider import BaseUniversitySpider


class LoughboroughSpider(BaseUniversitySpider):
    name = "loughborough"
    university_name = "Loughborough University"
    university_location = "Loughborough, England"
    needs_js = False

    start_urls = [
        "https://www.lboro.ac.uk/study/undergraduate/courses/",
    ]

    course_link_selector = "a.list__link"
    next_page_selector   = None

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Loughborough] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
