"""
scrapers/universities/northeastern_spider.py
───────────────────────────────────
Spider for Northeastern University London.
URL: https://www.nulondon.ac.uk/study/degrees/
"""

from scrapers.base_spider import BaseUniversitySpider


class NortheasternSpider(BaseUniversitySpider):
    name = "northeastern"
    university_name = "Northeastern University London"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.nulondon.ac.uk/study/degrees/",
    ]

    course_link_selector = "a[href*='/degrees/undergraduate/']"
    next_page_selector   = None

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Northeastern] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            abs_url = response.urljoin(href)
            if abs_url not in seen:
                seen.add(abs_url)
                yield self._make_request(abs_url, callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
