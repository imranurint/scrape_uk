"""
scrapers/universities/ntu_spider.py
───────────────────────────────────
Spider for Nottingham Trent University (NTU).
URL: https://www.ntu.ac.uk/study-and-courses/undergraduate/course-a-z
"""

from scrapers.base_spider import BaseUniversitySpider


class NTUSpider(BaseUniversitySpider):
    name = "ntu"
    university_name = "Nottingham Trent University"
    university_location = "Nottingham, England"
    needs_js = False

    start_urls = [
        "https://www.ntu.ac.uk/study-and-courses/undergraduate/course-a-z",
    ]

    # NTU listing uses /course/ paths
    course_link_selector = "a[href*='/course/']"
    next_page_selector   = "a[href*='result_page=']"

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.5,
    }

    def parse_course_list(self, response):
        """
        NTU lists courses with an A-Z pager.
        """
        # Find course links within the main list container
        links = response.css(
            "li.course-list__item a::attr(href), "
            "div.results-list a::attr(href), "
            "a[href*='/course/']::attr(href)"
        ).getall()

        self.logger.info(f"[NTU] Found {len(links)} links on {response.url}")

        for href in links:
            # Course URLs usually end with a number or slug
            if "/course/" in href:
                yield self._make_request(response.urljoin(href), callback=self.parse_course)

        # Follow A-Z pagination
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
