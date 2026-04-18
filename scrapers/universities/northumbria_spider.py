"""
scrapers/universities/northumbria_spider.py
─────────────────────────────────────────────
Spider for Northumbria University Newcastle.
URL: https://www.northumbria.ac.uk/study-at-northumbria/courses/
"""

from scrapers.base_spider import BaseUniversitySpider


class NorthumbriaSpider(BaseUniversitySpider):
    name = "northumbria"
    university_name = "Northumbria University"
    university_location = "Newcastle, England"
    needs_js = False

    start_urls = [
        "https://www.northumbria.ac.uk/study-at-northumbria/courses/",
    ]

    # Northumbria uses a search results list
    course_link_selector = "a.search-result__title-link"
    next_page_selector   = "a.pagination__next"

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.5,
    }

    def parse_course_list(self, response):
        """
        Northumbria listings are usually in search results.
        """
        links = response.css(
            "a.search-result__title-link::attr(href), "
            "div.course-card h3 a::attr(href), "
            "a[href*='/study-at-northumbria/courses/']::attr(href)"
        ).getall()

        self.logger.info(f"[Northumbria] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            abs_url = response.urljoin(href)
            # Filter out the listing page itself or irrelevant links
            if abs_url not in seen and "/courses/" in abs_url and "-ba-" in abs_url.lower() or "-bsc-" in abs_url.lower():
                seen.add(abs_url)
                yield self._make_request(abs_url, callback=self.parse_course)

        # Follow pagination
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
