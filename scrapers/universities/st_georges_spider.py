"""
scrapers/universities/st_georges_spider.py
────────────────────────────────────────────
Spider for St George's, University of London (City St George's).
URL: https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate%20degree
"""

from scrapers.base_spider import BaseUniversitySpider


class StGeorgesSpider(BaseUniversitySpider):
    name = "st_georges"
    university_name = "St George's, University of London"
    university_location = "London, England"
    needs_js = True

    start_urls = [
        "https://www.citystgeorges.ac.uk/prospective-students/courses",
        "https://www.citystgeorges.ac.uk/prospective-students/courses/undergraduate",
        "https://www.citystgeorges.ac.uk/prospective-students/courses/postgraduate",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree",
        # Subject-specific undergraduate URLs
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=arts+and+media",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=computing+and+computer+science",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=health+and+social+care",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=medicine",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=nursing",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=psychology",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=biomedical+science",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=radiography",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=physiotherapy",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=paramedic+science",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=undergraduate+degree&meta_subject_sand=sport+science",
        # Subject-specific postgraduate URLs
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=computing+and+computer+science",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=health+and+social+care",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=medicine",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=nursing",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=psychology",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=biomedical+science",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=radiography",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=physiotherapy",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=paramedic+science",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=sport+science",
        "https://www.citystgeorges.ac.uk/prospective-students/courses?meta_level_sand=postgraduate+taught+degree&meta_subject_sand=arts+and+media",
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 10.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [403, 429, 500, 502, 503, 504],
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"],
        },
    }

    def parse_course_list(self, response):
        """
        Extract all course links from St George's University pages
        """
        self.logger.info(f"[St George's] Processing {response.url}")
        
        # Strategy 1: Extract ALL links first
        all_links = response.css('a::attr(href)').getall()
        self.logger.info(f"[St George's] Total links found: {len(all_links)}")
        
        # Strategy 2: Filter for course-related URLs
        course_links = []
        for link in all_links:
            if not link:
                continue
            if link.startswith(("tel:", "mailto:", "javascript:", "#")):
                continue
            
            # St George's course URL patterns
            if any(pattern in link for pattern in [
                '/prospective-students/courses/',
                '/courses/',
                '/undergraduate/',
                '/postgraduate/',
                '/foundation/',
                '/short-courses/',
                '/research/',
                '/study/',
                'citystgeorges.ac.uk/courses',
                'citystgeorges.ac.uk/prospective-students/courses',
                # Individual course patterns - more specific
                '/course/',
                '/programme/',
                '/degree/',
                '/bachelor',
                '/master',
                '/phd',
                '/mba',
                '/msc',
                '/ba',
                '/bsc',
                '/beng',
                '/ma',
                '/march',
                '/llm',
                '/pgdip',
                '/pgcert',
                '/md',
                # Health Sciences specific
                '/nursing',
                '/medicine',
                '/health',
                '/biomedical',
                '/paramedic',
                '/radiography',
                '/physiotherapy',
                '/psychology',
                '/sport',
                '/clinical',
                '/midwifery',
                '/therapeutic',
                '/diagnostic',
                '/rehabilitation',
                # Technology specific
                '/computer-science',
                '/data-science',
                '/cyber-security',
                '/artificial-intelligence',
                '/informatics',
                '/technology',
                # Business & Law
                '/business',
                '/law',
                '/finance',
                '/economics',
                '/management',
                '/marketing',
                # Science & Research
                '/biology',
                '/chemistry',
                '/physics',
                '/mathematics',
                '/statistics',
                '/genetics',
                '/microbiology',
                # Social Sciences
                '/sociology',
                '/anthropology',
                '/geography',
                '/history',
                '/philosophy',
                '/politics',
                '/international-relations'
            ]):
                course_links.append(link)
        
        # Strategy 3: Remove duplicates and navigation
        final_links = []
        seen = set()
        for link in course_links:
            # Skip navigation/filter links and course listing pages
            if any(skip in link for skip in [
                '?query=',
                '?collection=',
                '?profile=',
                '?f.Level',
                'page=',
                '#',
                'courses',
                'prospective-students/courses',
                'prospective-students/courses/undergraduate',
                'prospective-students/courses/postgraduate',
                # Skip non-course pages
                '/apply/how-to-apply',
                '/about/schools/',
                '/barrister-pathway',
                '/academic-programmes/',
                '/information-for-parents-and-carers',
                '/pupillage-advisory-service',
                '/bar-training',
                '/msc-nursing-rpl',
                # Skip research pages
                '/research/',
                # Skip course listing pages with query parameters (these are listings, not individual courses)
                '?meta_level_sand=',
                '?meta_subject_sand='
            ]):
                continue
            
            abs_url = response.urljoin(link)
            if abs_url not in seen:
                seen.add(abs_url)
                final_links.append(abs_url)
        
        self.logger.info(f"[St George's] Found {len(final_links)} course links")
        
        # Strategy 4: Yield course detail requests
        for url in final_links:
            yield self._make_request(url, callback=self.parse_course)

        # Follow pagination if present
        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
