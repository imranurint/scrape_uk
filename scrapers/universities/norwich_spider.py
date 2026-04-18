"""
scrapers/universities/norwich_spider.py
───────────────────────────────────
Spider for Norwich University of the Arts.
URL: https://norwichuni.ac.uk/courses/find-your-course/
"""

from scrapers.base_spider import BaseUniversitySpider


class NorwichSpider(BaseUniversitySpider):
    name = "norwich"
    university_name = "Norwich University of the Arts"
    university_location = "Norwich, England"
    needs_js = False

    start_urls = [
        "https://norwichuni.ac.uk/courses/find-your-course/",
    ]

    course_link_selector = "a[href*='/courses/find-your-course/']:not([href$='/find-your-course/'])"
    next_page_selector   = "a.next.page-numbers"

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.5,
    }

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Norwich] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
