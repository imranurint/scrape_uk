"""
scrapers/universities/ntu_spider.py
───────────────────────────────────
Spider for Nottingham Trent University (NTU).
URL: https://www.ntu.ac.uk/study-and-courses/undergraduate/course-a-z
"""

from scrapers.base_spider import BaseUniversitySpider


class NTUSpider(BaseUniversitySpider):
    name = "ntu"
    university_name = "Nottingham Trent University"
    university_location = "Nottingham, England"
    needs_js = False

    start_urls = [
        "https://www.ntu.ac.uk/study-and-courses/undergraduate/course-a-z",
        "https://www.ntu.ac.uk/study-and-courses/postgraduate/subject-areas",
        "https://www.ntu.ac.uk/study-and-courses/postgraduate",
    ]

    course_link_selector = "a[href*='/course/'], a[href*='/courses/']"

    def parse_course_list(self, response):
        """
        NTU parser for undergraduate and postgraduate courses
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

        self.logger.info(f"[NTU] Found {len(course_links)} links on {response.url}")

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
