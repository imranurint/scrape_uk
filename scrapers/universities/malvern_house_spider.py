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

    start_urls = [
        "https://malvernhouse.com/our-courses/",
        "https://ncuk.malverninternational.com/",
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
    }

    def parse_course_list(self, response):
        """
        Extract all course links from Malvern House courses pages
        """
        self.logger.info(f"[MalvernHouse] Processing {response.url}")
        
        # Strategy 1: Extract ALL links first
        all_links = response.css('a::attr(href)').getall()
        self.logger.info(f"[MalvernHouse] Total links found: {len(all_links)}")
        
        # Strategy 2: Filter for course-related URLs
        course_links = []
        for link in all_links:
            if not link:
                continue
            if link.startswith(("tel:", "mailto:", "javascript:", "#")):
                continue
            
            # Malvern House course URL patterns
            if any(pattern in link for pattern in [
                '/our-courses/',
                '/course/',
                '/courses/',
                'teacher-training',
                'year-round-groups',
                'international-foundation-year',
                'international-year-one',
                'international-master',
                'pre-masters',
                'ncuk'
            ]):
                course_links.append(link)
        
        # Strategy 3: Remove duplicates and navigation
        final_links = []
        seen = set()
        for link in course_links:
            # Skip navigation/filter links
            if any(skip in link for skip in [
                '?query=',
                '?collection=',
                '?profile=',
                '?f.Level',
                'page=',
                '#',
                'login',
                'agent-login'
            ]):
                continue
            
            abs_url = response.urljoin(link)
            if abs_url not in seen:
                seen.add(abs_url)
                final_links.append(abs_url)
        
        self.logger.info(f"[MalvernHouse] Found {len(final_links)} course links")
        
        # Strategy 4: Yield course detail requests
        for url in final_links:
            yield self._make_request(url, callback=self.parse_course)

    def parse_course(self, response):
        """
        Extract course details from individual course pages
        """
        item = self._extract_and_normalise(response)
        if item:
            yield item
