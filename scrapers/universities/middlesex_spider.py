"""
scrapers/universities/middlesex_spider.py
──────────────────────────────────────────
Spider for Middlesex University London.
URL: https://www.mdx.ac.uk/courses
"""

from scrapers.base_spider import BaseUniversitySpider


class MiddlesexSpider(BaseUniversitySpider):
    name = "middlesex"
    university_name = "Middlesex University"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.mdx.ac.uk/courses",
    ]

    # Middlesex uses a search interface; we'll target the undergraduate listing
    course_link_selector = "a.link-overlay"
    next_page_selector   = "a.pagination__next"

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.5,
    }

    def parse_course_list(self, response):
        """
        Middlesex lists courses in cards. 
        Each card has a link or an overlay link.
        """
        # Broad selector to capture links in the course result area
        links = response.css(
            "div.course-card a::attr(href), "
            "a.course-card__link::attr(href), "
            "a.link-overlay::attr(href)"
        ).getall()

        self.logger.info(f"[Middlesex] Found {len(links)} links on {response.url}")

        for href in links:
            # Ensure we only follow undergraduate paths if that's the focus
            if "/undergraduate/" in href or "/courses/" in href:
                yield self._make_request(response.urljoin(href), callback=self.parse_course)

        # Follow pagination
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
