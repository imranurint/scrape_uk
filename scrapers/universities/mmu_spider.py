"""
scrapers/universities/mmu_spider.py
───────────────────────────────────
Spider for Manchester Metropolitan University (MMU).
URL: https://www.mmu.ac.uk/study/undergraduate/courses

NOTE: Uses Playwright to handle aggressive anti-bot measures.
"""

from scrapers.base_spider import BaseUniversitySpider


class MMUSpider(BaseUniversitySpider):
    name = "mmu"
    university_name = "Manchester Metropolitan University"
    university_location = "Manchester, England"
    
    needs_js = True

    start_urls = [
        "https://www.mmu.ac.uk/study/undergraduate/courses",
    ]

    wait_for_selector = ".course-listing__link"

    def parse_course_list(self, response):
        # MMU courses are often grouped by sector or A-Z
        links = response.css(".course-listing__link::attr(href), div.course-card a::attr(href)").getall()
        self.logger.info(f"[MMU] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            abs_url = response.urljoin(href)
            if abs_url not in seen and "/courses/" in abs_url:
                seen.add(abs_url)
                yield self._make_request(abs_url, callback=self.parse_course, use_js=True)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
