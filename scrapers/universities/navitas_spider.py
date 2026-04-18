"""
scrapers/universities/navitas_spider.py
───────────────────────────────────
Spider for NAVITAS Educational Group.
URL: https://www.navitas.com/study/courses/
"""

from scrapers.base_spider import BaseUniversitySpider


class NavitasSpider(BaseUniversitySpider):
    name = "navitas"
    university_name = "Navitas Group"
    university_location = "Multiple (UK)"
    needs_js = False

    start_urls = [
        "https://www.navitas.com/study/courses/?location=united-kingdom",
    ]

    # Navitas uses a table structure in their central hub
    course_link_selector = "a.course-website"
    next_page_selector   = "a.page-link[aria-label='Next']"

    def parse_course_list(self, response):
        """
        Navitas hub lists rows of courses with the college name.
        """
        rows = response.css("table.table-striped tbody tr")
        self.logger.info(f"[Navitas] Found {len(rows)} course rows on {response.url}")

        for row in rows:
            href = row.css("a.course-website::attr(href)").get()
            college = row.css("td:nth-child(2)::text").get()
            
            if href:
                # We tag the item with the specific partner college name
                meta = {"partner_college": college.strip() if college else None}
                yield self._make_request(
                    response.urljoin(href), 
                    callback=self.parse_course,
                    cb_kwargs={"partner": college}
                )

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response, partner=None):
        item = self._extract_and_normalise(response)
        if item:
            # Overwrite university name with the specific partner college
            if partner:
                item["university"]["name"] = f"Navitas - {partner}"
            yield item
