"""
scrapers/universities/lsbu_spider.py
───────────────────────────────────
Spider for London South Bank University (LSBU).
URL: https://www.lsbu.ac.uk/study/course-finder
"""

import json
import re
from urllib.parse import parse_qs, urlencode, urlparse

from scrapers.base_spider import BaseUniversitySpider


class LSBUSpider(BaseUniversitySpider):
    name = "lsbu"
    university_name = "London South Bank University"
    university_location = "London, England"
    
    # Enable JavaScript for dynamic content
    needs_js = True
    
    # Multiple browser strategies
    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,  # Reduce to avoid blocking
        "DOWNLOAD_DELAY": 8.0,  # Slower for respect
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",  # Try different browsers
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled"]
        }
    }

    start_urls = [
        "https://www.lsbu.ac.uk/study/course-finder",
        "https://www.lsbu.ac.uk/study/postgraduate/masters-courses",
        "https://www.lsbu.ac.uk/study/undergraduate",
        "https://www.lsbu.ac.uk/study/postgraduate",
    ]

    course_link_selector = "a[href*='/course/'], a[href*='/courses/']"

    def parse_course_list(self, response):
        """
        LSBU parser for undergraduate and postgraduate courses
        """
        self.logger.info(f"[LSBU] Processing {response.url}")
        
        # Strategy 1: Extract ALL links first
        all_links = response.css('a::attr(href)').getall()
        self.logger.info(f"[LSBU] Total links found: {len(all_links)}")
        
        # Strategy 2: Filter for course-related URLs
        course_links = []
        for link in all_links:
            if not link:
                continue
            if link.startswith(("tel:", "mailto:", "javascript:", "#")):
                continue
            
            # Multiple LSBU course URL patterns
            if any(pattern in link for pattern in [
                '/course/',
                '/courses/',
                '/study/course',
                'course-finder/',
                'undergraduate/',
                'postgraduate/',
                'masters-courses/'
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
                '#'
            ]):
                continue
            
            abs_url = response.urljoin(link)
            if abs_url not in seen:
                seen.add(abs_url)
                final_links.append(abs_url)
        
        self.logger.info(f"[LSBU] Found {len(final_links)} course links on {response.url}")
        
        # Strategy 4: Yield course detail requests
        for url in final_links:
            yield self._make_request(url, callback=self.parse_course)

        # Follow pagination if present
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        """
        Extract course details from individual course pages
        """
        item = self._extract_and_normalise(response)
        if item:
            yield item