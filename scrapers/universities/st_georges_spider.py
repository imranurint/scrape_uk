"""
scrapers/universities/st_georges_spider.py
────────────────────────────────────────────
Spider for St George's, University of London (City St George's).
URL: https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate%20degree
"""

from scrapers.base_spider import BaseUniversitySpider


class StGeorgesSpider(BaseUniversitySpider):
    name = "st_georges"
    university_name = "St George's, University of London"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate%20degree",
    ]

    course_link_selector = "a.card__anchor.card__details"
    next_page_selector   = "a.pagination__controls__button--next"

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[St George's] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
