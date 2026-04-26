"""
scrapers/universities/middlesex_spider.py
──────────────────────────────────────────
Spider for Middlesex University London.
URL: https://www.mdx.ac.uk/courses
"""

from scrapers.base_spider import BaseUniversitySpider


class MiddlesexSpider(BaseUniversitySpider):
    name = "middlesex"
    university_name = "Middlesex University"
    university_location = "London, England"
    needs_js = True
    wait_for_selector = "body"

    start_urls = [
        "https://www.mdx.ac.uk/courses",
    ]

    # Course list is rendered client-side.
    course_link_selector = "main a[href*='/courses/']"
    next_page_selector = ""

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 2.5,
    }

    def parse_course_list(self, response):
        """
        Middlesex renders course cards via JS. Pull all rendered course-like links
        and filter out listing/filter URLs.
        """
        links = response.css("main a[href*='/courses/']::attr(href)").getall()

        self.logger.info(f"[Middlesex] Found {len(links)} links on {response.url}")

        seen = set()
        for href in links:
            if not href:
                continue
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            abs_url = response.urljoin(href)
            if "/courses/" not in abs_url:
                continue
            if abs_url.rstrip("/") == response.url.rstrip("/"):
                continue
            if "?" in abs_url or "#" in abs_url:
                continue

            # Keep only likely course detail pages.
            if not any(
                token in abs_url
                for token in (
                    "/courses/undergraduate/",
                    "/courses/postgraduate/",
                    "/courses/short-courses-and-cpd/",
                    "/courses/foundation/",
                    "/courses/research-degrees/",
                )
            ):
                continue

            if abs_url in seen:
                continue
            seen.add(abs_url)
            yield self._make_request(abs_url, callback=self.parse_course, use_js=False)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
