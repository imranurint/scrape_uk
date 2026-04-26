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

    course_urls = [
        "https://malvernhouse.com/our-courses/teacher-training/",
        "https://malvernhouse.com/our-courses/year-round-groups/",
    ]

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
        for url in self.course_urls:
            yield Request(
                url=url,
                callback=self.parse_course,
                errback=self._errback,
                meta={
                        "playwright": True,
                    "playwright_include_page": False,
                    "playwright_page_methods": [
                        PageMethod("wait_for_timeout", 1500),
                    ],
                },
            )

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
