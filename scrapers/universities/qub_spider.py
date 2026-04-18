"""
scrapers/universities/qub_spider.py
───────────────────────────────────
Spider for Queen's University Belfast (QUB).
URL: https://www.qub.ac.uk/courses/undergraduate/
"""

from scrapers.base_spider import BaseUniversitySpider


class QUBSpider(BaseUniversitySpider):
    name = "qub"
    university_name = "Queen's University Belfast"
    university_location = "Belfast, Northern Ireland"
    needs_js = False

    start_urls = [
        "https://www.qub.ac.uk/courses/undergraduate/",
    ]

    # QUB lists all courses on a single page with direct links
    course_link_selector = "a[href^='/home/courses/undergraduate/']"
    next_page_selector   = None

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.0,
    }

    def parse_course_list(self, response):
        """
        QUB lists all 400+ courses on the front undergraduate page.
        """
        links = response.css(
            "a[href^='/home/courses/undergraduate/']::attr(href), "
            "div.course-finder-results a::attr(href)"
        ).getall()

        self.logger.info(f"[QUB] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            abs_url = response.urljoin(href)
            if abs_url not in seen and "/undergraduate/" in abs_url:
                seen.add(abs_url)
                yield self._make_request(abs_url, callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
