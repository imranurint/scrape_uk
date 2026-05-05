"""
scrapers/universities/northeastern_spider.py
───────────────────────────────────
Spider for Northeastern University London.
URL: https://www.nulondon.ac.uk/study/degrees/
"""

from scrapers.base_spider import BaseUniversitySpider


class NortheasternSpider(BaseUniversitySpider):
    name = "northeastern"
    university_name = "Northeastern University London"
    university_location = "London, England"
    needs_js = False

    start_urls = [
        "https://www.nulondon.ac.uk/study/degrees/",
        "https://www.nulondon.ac.uk/study/undergraduate-degrees/",
        "https://www.nulondon.ac.uk/degrees/postgraduate/",
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 3.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def parse_course_list(self, response):
        """
        Extract all course links from Northeastern University London pages
        """
        self.logger.info(f"[Northeastern] Processing {response.url}")
        
        # Strategy 1: Extract ALL links first
        all_links = response.css('a::attr(href)').getall()
        self.logger.info(f"[Northeastern] Total links found: {len(all_links)}")
        
        # Strategy 2: Filter for course-related URLs
        course_links = []
        for link in all_links:
            if not link:
                continue
            if link.startswith(("tel:", "mailto:", "javascript:", "#")):
                continue
            
            # Northeastern course URL patterns
            if any(pattern in link for pattern in [
                '/degrees/undergraduate/',
                '/degrees/postgraduate/',
                '/degrees/degree-apprenticeships/',
                '/study/degrees/',
                'nulondon.ac.uk/degrees/'
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
        
        self.logger.info(f"[Northeastern] Found {len(final_links)} course links")
        
        # Strategy 4: Yield course detail requests
        for url in final_links:
            yield self._make_request(url, callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
