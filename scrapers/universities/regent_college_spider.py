"""
scrapers/universities/regent_college_spider.py
─────────────────────────────────────────────
Spider for Regent College London (RCL).
URL: https://www.rcl.ac.uk/courses/search/
"""

from scrapers.base_spider import BaseUniversitySpider


class RegentCollegeSpider(BaseUniversitySpider):
    name = "regent_college"
    university_name = "Regent College London"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.rcl.ac.uk/courses/",
        "https://www.rcl.ac.uk/courses/subjects/business/",
        "https://www.rcl.ac.uk/courses/subjects/engineering-and-computing/",
        "https://www.rcl.ac.uk/courses/subjects/health-and-sports-science/",
        "https://www.rcl.ac.uk/courses/subjects/law/",
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 3.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def parse_course_list(self, response):
        """
        Extract all course links from Regent College London pages
        """
        self.logger.info(f"[Regent College] Processing {response.url}")
        
        # Strategy 1: Extract ALL links first
        all_links = response.css('a::attr(href)').getall()
        self.logger.info(f"[Regent College] Total links found: {len(all_links)}")
        
        # Strategy 2: Filter for course-related URLs
        course_links = []
        for link in all_links:
            if not link:
                continue
            if link.startswith(("tel:", "mailto:", "javascript:", "#")):
                continue
            
            # Regent College course URL patterns
            if any(pattern in link for pattern in [
                '/courses/detail/',
                '/courses/subjects/',
                '/courses/search/',
                'rcl.ac.uk/courses/'
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
                'subjects/',
                'search/'
            ]):
                continue
            
            abs_url = response.urljoin(link)
            if abs_url not in seen:
                seen.add(abs_url)
                final_links.append(abs_url)
        
        self.logger.info(f"[Regent College] Found {len(final_links)} course links")
        
        # Strategy 4: Yield course detail requests
        for url in final_links:
            yield self._make_request(url, callback=self.parse_course)

        # Follow pagination if present
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
