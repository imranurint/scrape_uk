"""
scrapers/universities/lsbu_spider.py
───────────────────────────────────
Spider for London South Bank University (LSBU).
URL: https://www.lsbu.ac.uk/study/course-finder
"""

from scrapers.base_spider import BaseUniversitySpider


class LSBUSpider(BaseUniversitySpider):
    name = "lsbu"
    university_name = "London South Bank University"
    university_location = "London, England"
    needs_js = True
    wait_for_selector = "a[href*='/study/course-finder/']"

    start_urls = [
        "https://www.lsbu.ac.uk/study/course-finder?num_ranks=20&query=&collection=lsbu-meta",
    ]

    course_link_selector = ".course-finder-results h2 a"
    next_page_selector   = "a.next"

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        self.logger.info(f"[LSBU] Found {len(links)} links on {response.url}")

        for href in links:
            if href.startswith(("tel:", "mailto:", "javascript:")):
                continue

            url = response.urljoin(href)
            if "/study/course-finder/" not in url:
                continue
            if "/study/course-finder?" in url:
                continue
            if url.rstrip("/") == response.url.rstrip("/"):
                continue

            yield self._make_request(url, callback=self.parse_course)

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
