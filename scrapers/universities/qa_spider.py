"""
scrapers/universities/qa_spider.py
───────────────────────────────────
Spider for QA Higher Education.
URL: https://qahighereducation.com/courses/

Uses AJAX 'Load More'. We use Playwright for reliable discovery.
"""

from scrapers.base_spider import BaseUniversitySpider


class QASpider(BaseUniversitySpider):
    name = "qa"
    university_name = "QA Higher Education"
    university_location = "Multiple (UK)"
    
    # Needs JS for 'Load More' pagination
    needs_js = True

    start_urls = [
        "https://qahighereducation.com/courses/",
    ]

    wait_for_selector = "a.course-list-single"

    def parse_course_list(self, response):
        links = response.css("a.course-list-single::attr(href)").getall()
        self.logger.info(f"[QA] Found {len(links)} links on {response.url}")

        for href in links:
            yield self._make_request(response.urljoin(href), callback=self.parse_course)

        # Note: In a production run with Playwright, we would use a script to click 'Load More'
        # until all links are visible.
        # For this version, we scrape the initial visible list.
