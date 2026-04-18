"""
scrapers/universities/rgu_spider.py
───────────────────────────────────
Spider for Robert Gordon University (RGU).
URL: https://www.rgu.ac.uk/study/courses
"""

from scrapers.base_spider import BaseUniversitySpider


class RGUSpider(BaseUniversitySpider):
    name = "rgu"
    university_name = "Robert Gordon University"
    university_location = "Aberdeen, Scotland"
    needs_js = False

    start_urls = [
        "https://www.rgu.ac.uk/study/courses",
    ]

    course_link_selector = "a.link[href*='/study/courses/']"
    next_page_selector   = None

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.0,
    }

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[RGU] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
