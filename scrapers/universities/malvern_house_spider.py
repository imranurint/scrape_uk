"""
scrapers/universities/malvern_house_spider.py
───────────────────────────────────
Spider for Malvern House International.

Malvern House's front-end cards are not reliably exposed in the DOM, so this
spider uses the WordPress REST API to discover the course pages underneath
/our-courses/ and then scrapes those detail pages normally.
"""

from __future__ import annotations

import json
from urllib.parse import urlencode

from scrapy import Request
from scrapy_playwright.page import PageMethod

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
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse_api_courses,
                errback=self._errback,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_timeout", 1500),
                    ],
                },
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

    async def parse_api_courses(self, response):
        page = response.meta.get("playwright_page")
        try:
            pages = await page.evaluate(
                """async ({ apiUrl, parentPageId }) => {
                    const url = new URL(apiUrl);
                    url.searchParams.set('parent', String(parentPageId));
                    url.searchParams.set('per_page', '100');
                    url.searchParams.set('orderby', 'menu_order');
                    url.searchParams.set('order', 'asc');
                    url.searchParams.set('status', 'publish');

                    const res = await fetch(url.toString(), { credentials: 'include' });
                    if (!res.ok) {
                        throw new Error(`HTTP ${res.status}`);
                    }
                    return await res.json();
                }""",
                {"apiUrl": self.api_url, "parentPageId": self.parent_page_id},
            )
        except Exception as exc:
            self.logger.error("[Malvern House] Failed to fetch WP API from browser", error=str(exc), url=response.url)
            return
        finally:
            if page:
                await page.close()

        if not isinstance(pages, list):
            self.logger.error("[Malvern House] Unexpected WP API payload", url=response.url)
            return

        self.logger.info(f"[Malvern House] API returned {len(pages)} child pages")

        requests = []
        for page in pages:
            url = page.get("link") or ""
            if not url:
                continue
            if not url.startswith("https://malvernhouse.com/"):
                continue
            if "/our-courses/" not in url:
                continue
            requests.append(self._make_request(url, callback=self.parse_course, use_js=True))

        return requests

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
