"""
scrapers/universities/lsbu_spider.py
───────────────────────────────────
Spider for London South Bank University (LSBU).
URL: https://www.lsbu.ac.uk/study/course-finder
"""

from scrapers.base_spider import BaseUniversitySpider
from scrapy.http import Request
from scrapy_playwright.page import PageMethod


class LSBUSpider(BaseUniversitySpider):
    name = "lsbu"
    university_name = "London South Bank University"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.lsbu.ac.uk/study/course-finder?num_ranks=20&query=&collection=lsbu-meta",
    ]

    course_link_selector = ".course-finder-results h2 a"
    next_page_selector   = "a.next"

    def start_requests(self):
        for url in self.start_urls:
            # LSBU finder is JS-driven and often blocked behind consent state.
            # Accept cookies if the banner exists, then wait for network idle.
            yield Request(
                url=url,
                callback=self.parse_course_list,
                errback=self._errback,
                meta={
                    "playwright": True,
                    "playwright_include_page": False,
                    "playwright_page_methods": [
                        PageMethod(
                            "evaluate",
                            """() => {
                                const btn = document.querySelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll');
                                if (btn) btn.click();
                            }""",
                        ),
                        PageMethod("wait_for_timeout", 1500),
                    ],
                },
            )

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        if not links:
            # Fallback selectors for markup variations.
            links = response.css("a[href*='/study/course-finder/']::attr(href)").getall()
        if not links:
            links = response.css("a[href*='/study/courses/']::attr(href)").getall()
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
