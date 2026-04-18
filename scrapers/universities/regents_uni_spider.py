"""
scrapers/universities/regents_uni_spider.py
───────────────────────────────────
Spider for Regent's University London.
URL: https://www.regents.ac.uk/study/undergraduate

NOTE: This site uses aggressive CDN protection.
We use Playwright (needs_js=True) to bypass potential JS challenges.
"""

from scrapers.base_spider import BaseUniversitySpider


class RegentsUniSpider(BaseUniversitySpider):
    name = "regents_uni"
    university_name = "Regent's University London"
    university_location = "London, England"
    
    # Enabling Playwright for JS challenges/Cloudflare bypass
    needs_js = True

    start_urls = [
        "https://www.regents.ac.uk/study/undergraduate",
    ]

    # Specific wait to ensure content loads past any splash screen
    wait_for_selector = "a[href*='/undergraduate/']"

    def parse_course_list(self, response):
        links = response.css("a[href*='/undergraduate/']::attr(href)").getall()
        self.logger.info(f"[Regent's Uni] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            abs_url = response.urljoin(href)
            # Filter out parent pages and keep specific degree paths
            if abs_url not in seen and "/ba-hons-" in abs_url or "/bsc-hons-" in abs_url:
                seen.add(abs_url)
                yield self._make_request(abs_url, callback=self.parse_course, use_js=True)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
