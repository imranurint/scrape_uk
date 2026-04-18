"""
scrapers/universities/malvern_house_spider.py
───────────────────────────────────
Spider for Malvern House International.
URL: https://malvernhouse.com/courses/

NOTE: Uses Playwright to bypass potential Cloudflare human verification.
"""

from scrapers.base_spider import BaseUniversitySpider


class MalvernHouseSpider(BaseUniversitySpider):
    name = "malvern_house"
    university_name = "Malvern House International"
    university_location = "London, England"
    
    # Enabling Playwright for human verification challenges
    needs_js = True

    start_urls = [
        "https://malvernhouse.com/courses/",
    ]

    wait_for_selector = ".course-card a"

    def parse_course_list(self, response):
        links = response.css(".course-card a::attr(href), h2.entry-title a::attr(href)").getall()
        self.logger.info(f"[Malvern House] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course, use_js=True)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
