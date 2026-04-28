"""
scrapers/universities/regent_college_spider.py
─────────────────────────────────────────────
Spider for Regent College London (RCL).
URL: https://www.rcl.ac.uk/courses/search/
"""

from scrapers.base_spider import BaseUniversitySpider


class RegentCollegeSpider(BaseUniversitySpider):
    name = "regent_college"
    university_name = "Regent College London"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.rcl.ac.uk/courses/search/",
    ]

    course_link_selector = "a.course-search-card"
    next_page_selector   = None

    def parse_course_list(self, response):
        from scrapy_playwright.page import PageMethod
        req = self._make_request(
            response.url,
            callback=self.parse_course_list_js,
            use_js=True,
        )
        req = req.replace(dont_filter=True)
        req.meta.update({
            "playwright_page_methods": [
                PageMethod("click", "button.facetwp-load-more"),
                PageMethod("wait_for_timeout", 3000),
            ]
        })
        return req

    def parse_course_list_js(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Regent College] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
