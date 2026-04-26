"""
scrapers/universities/navitas_spider.py
───────────────────────────────────
Spider for NAVITAS Educational Group.
URL: https://www.navitas.com/study/courses/
"""

from scrapers.base_spider import BaseUniversitySpider
from scrapy_playwright.page import PageMethod


class NavitasSpider(BaseUniversitySpider):
    name = "navitas"
    university_name = "Navitas Group"
    university_location = "Multiple (UK)"
    needs_js = True

    start_urls = [
        "https://www.navitas.com/study/courses/",
    ]

    # Navitas uses a search-based SPA now. 
    # We trigger a search and wait for the results table.
    custom_settings = {
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,
    }

    def _make_request(self, url, callback, **kwargs):
        req = super()._make_request(url, callback, **kwargs)
        if url == self.start_urls[0]:
            # Initial search trigger for the course list
            req.meta["playwright_page_methods"] = [
                PageMethod("wait_for_selector", 'input[name="search"]'),
                PageMethod("click", 'input[name="search"]'),
                PageMethod("wait_for_selector", "table tr td", timeout=20000),
                PageMethod("wait_for_timeout", 2000), # Let JS settle
            ]
        return req

    def parse_course_list(self, response):
        """
        Navitas hub lists rows of courses with the college name.
        """
        # Filter for UK results in the parser since the URL param is unreliable with Playwright re-renders
        rows = response.css("tr")
        self.logger.info(f"[Navitas] Found {len(rows)} total rows on {response.url}")

        valid_count = 0
        for row in rows:
            cells = row.css("td")
            if len(cells) < 3:
                continue
            
            country = cells[2].css("::text").get()
            if country and "United Kingdom" in country:
                href = row.css("a::attr(href)").get()
                college = cells[1].css("::text").get()
                
                if href:
                    valid_count += 1
                    # We tag the item with the specific partner college name
                    yield self._make_request(
                        response.urljoin(href), 
                        callback=self.parse_course,
                        cb_kwargs={"partner": college.strip() if college else None},
                        use_js=True # Detail pages might also need JS
                    )

        self.logger.info(f"[Navitas] Found {valid_count} UK course links")

    def parse_course(self, response, partner=None):
        item = self._extract_and_normalise(response)
        if item:
            # Overwrite university name with the specific partner college
            if partner:
                item["university"]["name"] = f"Navitas - {partner}"
            yield item
