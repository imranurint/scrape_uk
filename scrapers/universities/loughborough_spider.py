"""
scrapers/universities/loughborough_spider.py
───────────────────────────────────
Spider for Loughborough University.
URL: https://www.lboro.ac.uk/study/undergraduate/courses/
"""

from scrapers.base_spider import BaseUniversitySpider


class LoughboroughSpider(BaseUniversitySpider):
    name = "loughborough"
    university_name = "Loughborough University"
    university_location = "Loughborough, England"
    needs_js = False

    start_urls = [
        "https://www.lboro.ac.uk/study/undergraduate/courses/",
        "https://www.lboro.ac.uk/study/postgraduate/masters-degrees/",
    ]

    course_link_selector = "a[href*='/courses/'], a[href*='/masters-'], a.course-link"

    def parse_course_list(self, response):
        """
        Loughborough parser for undergraduate and postgraduate courses
        """
        # Multiple selector strategies for different page types
        links = response.css(
            "a[href*='/courses/']::attr(href), "
            "a[href*='/masters-']::attr(href), "
            "a.course-link::attr(href), "
            "div.course-item a::attr(href), "
            "li.course-listing a::attr(href), "
            "a.list__link::attr(href)"
        ).getall()

        # Filter for course URLs only
        course_links = [
            link for link in links 
            if '/courses/' in link or '/masters-' in link
        ]

        self.logger.info(f"[Loughborough] Found {len(course_links)} links on {response.url}")

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
