"""
scrapers/universities/qub_spider.py
───────────────────────────────────
Spider for Queen's University Belfast (QUB).
URL: https://www.qub.ac.uk/courses/undergraduate/
"""

from scrapers.base_spider import BaseUniversitySpider


class QUBSpider(BaseUniversitySpider):
    name = "qub"
    university_name = "Queen's University Belfast"
    university_location = "Belfast, Northern Ireland"
    needs_js = True

    start_urls = [
        "https://www.qub.ac.uk/courses/undergraduate/",
        "https://www.qub.ac.uk/courses/postgraduate-taught/",
    ]

    # QUB lists all courses on a single page with direct links
    course_link_selector = "a[href^='/home/courses/']"
    next_page_selector   = None

    custom_settings = {
    "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    "DOWNLOAD_DELAY": 8.0,  # Slower for respect
    "RANDOMIZE_DOWNLOAD_DELAY": True,
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

    def parse_course_list(self, response):
    """
    Updated QUB parser with multiple selector strategies
    """
    # Strategy 1: Common course link patterns
    links = response.css(
        "a[href*='/courses/undergraduate/']::attr(href), "
        "a[href*='/courses/postgraduate-taught/']::attr(href), "
        "a[href*='/courses/postgraduate-research/']::attr(href), "
        "a.course-link::attr(href), "
        "a.course-title::attr(href), "
        "div.course-item a::attr(href), "
        "div.course-card a::attr(href), "
        "div.course-listing a::attr(href), "
        "li.course a::attr(href)"
    ).getall()

    # Strategy 2: URL pattern matching
    all_links = response.css('a::attr(href)').getall()
    filtered_links = [
        link for link in all_links 
        if '/courses/' in link and (
            '/undergraduate/' in link or 
            '/postgraduate-' in link
        )
    ]
    
    # Combine both strategies
    all_course_links = list(set(links + filtered_links))
    
    self.logger.info(f"[QUB] Found {len(all_course_links)} links on {response.url}")

    seen = set()
    for href in all_course_links:
        abs_url = response.urljoin(href)
        if abs_url not in seen:
            seen.add(abs_url)
            yield self._make_request(abs_url, callback=self.parse_course)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
