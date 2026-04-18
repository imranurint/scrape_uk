"""
scrapers/universities/brookes_spider.py
───────────────────────────────────
Spider for Oxford Brookes University.
URL: https://www.brookes.ac.uk/courses/undergraduate/
"""

from scrapers.base_spider import BaseUniversitySpider


from scrapy_playwright.page import PageMethod

class BrookesSpider(BaseUniversitySpider):
    name = "brookes"
    university_name = "Oxford Brookes University"
    university_location = "Oxford, England"
    
    # Brookes search requires JS to render results
    needs_js = True
    wait_for_selector = "a[href*='/s/redirect']"

    start_urls = [
        "https://search.brookes.ac.uk/s/search.html?collection=oxford-brookes~sp-course-finder&f.Study+level%7CcourseLevel=undergraduate&query=",
    ]

    course_link_selector = "a[href*='/s/redirect']"
    next_page_selector   = "a.next"

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 3.0,  # Brookes can be sensitive to rate
        "ROBOTSTXT_OBEY": False,
    }

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[Oxford Brookes] Found {len(links)} links on {response.url}")

        for href in links:
            req = self._make_request(response.urljoin(href), callback=self.parse_course)
            req.meta["playwright_page_methods"] = [
                PageMethod("wait_for_load_state", "networkidle"),
            ]
            yield req

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
