"""
scrapers/universities/sheffield_hallam_spider.py
──────────────────────────────────────────────────
Spider for Sheffield Hallam University.
URL: https://www.shu.ac.uk/courses
"""

from scrapers.base_spider import BaseUniversitySpider


class SheffieldHallamSpider(BaseUniversitySpider):
    name = "sheffield_hallam"
    university_name = "Sheffield Hallam University"
    university_location = "Sheffield, England"
    needs_js = False

    start_urls = [
        "https://www.shu.ac.uk/courses?page=1",
    ]

    course_link_selector = "a.m-snippet__link"
    next_page_selector   = "button.m-pagination__control--next" # Or query param based

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Sheffield Hallam] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

        # Handle numeric pagination via query param increment
        current_page = int(response.url.split("page=")[-1] if "page=" in response.url else 1)
        if len(links) >= 10:  # If we got a full page, try next
            next_url = f"https://www.shu.ac.uk/courses?page={current_page + 1}"
            yield self._make_request(next_url, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
