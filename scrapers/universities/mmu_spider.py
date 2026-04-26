"""
scrapers/universities/mmu_spider.py
───────────────────────────────────
Spider for Manchester Metropolitan University (MMU).
URL: https://www.mmu.ac.uk/study/undergraduate/courses/A

MMU's old listing endpoint can redirect to a generic search page. This spider
uses the A-Z undergraduate course pages and follows detail links under
/study/undergraduate/course/.
"""

from scrapers.base_spider import BaseUniversitySpider


class MMUSpider(BaseUniversitySpider):
    name = "mmu"
    university_name = "Manchester Metropolitan University"
    university_location = "Manchester, England"

    needs_js = True
    wait_for_selector = "a[href*='/study/undergraduate/course/']"

    start_urls = [
        "https://www.mmu.ac.uk/study/undergraduate/courses/A",
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.0,
    }

    def parse_course_list(self, response):
        links = response.css("a[href]::attr(href)").getall()
        self.logger.info(f"[MMU] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            if not href:
                continue
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            abs_url = response.urljoin(href)
            if abs_url in seen:
                continue
            seen.add(abs_url)

            # Follow letter index pages for wider coverage.
            if "/study/undergraduate/courses/" in abs_url:
                suffix = abs_url.rstrip("/").split("/study/undergraduate/courses/")[-1]
                if len(suffix) == 1 and suffix.isalpha():
                    yield self._make_request(abs_url, callback=self.parse_course_list, use_js=True)
                continue

            # Course detail pages are stable via normal Scrapy requests.
            if "/study/undergraduate/course/" in abs_url:
                yield self._make_request(abs_url, callback=self.parse_course, use_js=False)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
