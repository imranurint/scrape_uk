"""
scrapers/universities/oieg_spider.py
───────────────────────────────────
Spider for Oxford International Education Group (OIEG).
URL: https://www.oxfordinternational.com/courses/

Covers: Ravensbourne OIEG, DMU, Dundee, etc.
"""

from scrapers.base_spider import BaseUniversitySpider


class OIEGSpider(BaseUniversitySpider):
    name = "oieg"
    university_name = "Oxford International Education Group"
    university_location = "Multiple (UK)"
    needs_js = False

    start_urls = [
        "https://www.oxfordinternational.com/courses/",
    ]

    # OIEG uses card links
    course_link_selector = "a[href*='/courses/detail/']"
    next_page_selector   = ".facetwp-pager a.facetwp-page.next"

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[OIEG] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            # Try to extract the partner university from the page text
            partner = response.css(".course-partner-logo img::attr(alt)").get()
            if partner:
                item["university"]["name"] = f"OIEG - {partner}"
            yield item
