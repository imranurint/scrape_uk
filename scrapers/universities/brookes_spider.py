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
    # wait_for_selector = "a[href*='/s/redirect']"

    start_urls = [
        "https://www.brookes.ac.uk/study/courses/undergraduate",
        "https://www.brookes.ac.uk/study/courses/postgraduate/masters",
    ]

    # Remove search-based approach, use direct course listings
    course_link_selector = "a[href*='/course/'], a[href*='/courses/']"


    def parse_course_list(self, response):
        """
        Oxford Brookes parser for undergraduate and postgraduate courses
        """
        # Multiple selector strategies for different page types
        links = response.css(
            "a[href*='/course/']::attr(href), "
            "a[href*='/courses/']::attr(href), "
            "a.course-link::attr(href), "
            "div.course-item a::attr(href), "
            "li.course-listing a::attr(href)"
        ).getall()

        # Filter for course URLs only
        course_links = [
            link for link in links 
            if '/course/' in link or '/courses/' in link
        ]

        self.logger.info(f"[Brookes] Found {len(course_links)} links on {response.url}")

        seen = set()
        for href in course_links:
            abs_url = response.urljoin(href)
            if abs_url not in seen:
                seen.add(abs_url)
                yield self._make_request(abs_url, callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
