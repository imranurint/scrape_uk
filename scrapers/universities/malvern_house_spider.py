"""
scrapers/universities/malvern_house_spider.py
───────────────────────────────────
Spider for Malvern House International.

Malvern House's front-end cards are not reliably exposed in the DOM, so this
spider uses the WordPress REST API to discover the course pages underneath
/our-courses/ and then scrapes those detail pages normally.
"""

from __future__ import annotations

from urllib.parse import urlencode

from scrapy import Request

from scrapers.base_spider import BaseUniversitySpider


class MalvernHouseSpider(BaseUniversitySpider):
    name = "malvern_house"
    university_name = "Malvern House International"
    university_location = "London, England"
    needs_js = True

    api_url = "https://malvernhouse.com/wp-json/wp/v2/pages"
    parent_page_id = 223

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 5,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        },
        "PLAYWRIGHT_CONTEXT_ARGS": {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    }

    start_urls = ["https://malvernhouse.com/our-courses/"]

    def start_requests(self):
        yield Request(
            url=self._build_api_url(),
            callback=self.parse_api_courses,
            errback=self._errback,
        )

    def _build_api_url(self) -> str:
        params = {
            "parent": str(self.parent_page_id),
            "per_page": "100",
            "orderby": "menu_order",
            "order": "asc",
            "status": "publish",
        }
        return f"{self.api_url}?{urlencode(params)}"

    def parse_api_courses(self, response):
        try:
            pages = response.json()
        except Exception as exc:
            self.logger.error("[Malvern House] Failed to parse WP API response", error=str(exc), url=response.url)
            return

        if not isinstance(pages, list):
            self.logger.error("[Malvern House] Unexpected WP API payload", url=response.url)
            return

        self.logger.info(f"[Malvern House] API returned {len(pages)} child pages")

        for page in pages:
            url = page.get("link") or ""
            if not url:
                continue
            if not url.startswith("https://malvernhouse.com/"):
                continue
            if "/our-courses/" not in url:
                continue
            yield self._make_request(url, callback=self.parse_course, use_js=True)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
