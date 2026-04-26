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
    needs_js = False

    api_url = "https://lsbu-search.funnelback.squiz.cloud/s/search.json"
    page_size = 20

    start_urls = [
        "https://www.lsbu.ac.uk/study/course-finder?num_ranks=20&query=&collection=lsbu-meta",
    ]

    course_link_selector = ".course-finder-results h2 a"
    next_page_selector   = "a.next"

    def start_requests(self):
        yield self._make_request(self._build_api_url(start_rank=1), callback=self.parse_api_list)

    def _build_api_url(self, start_rank: int) -> str:
        params = {
            "collection": "lsbu~sp-courses-meta",
            "profile": "_default",
            "query": "!nullsearch",
            "start_rank": str(start_rank),
            "sort": "relevance",
            "num_ranks": str(self.page_size),
            "f.Level_new|courseLevel": "undergraduate",
        }
        return f"{self.api_url}?{urlencode(params)}"

    def parse_api_list(self, response):
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("[LSBU] API returned non-JSON payload", url=response.url)
            return

        packet = payload.get("response", {}).get("resultPacket", {})
        results = packet.get("results", []) or []
        summary = packet.get("resultsSummary", {}) or {}

        self.logger.info(
            f"[LSBU] API returned {len(results)} results on {response.url}"
        )

        for row in results:
            url = row.get("liveUrl") or row.get("indexUrl") or ""
            if not url:
                continue
            if "/study/course-finder/" not in url:
                continue
            if "?" in url:
                url = url.split("?", 1)[0]
            yield self._make_request(url, callback=self.parse_course)

        total = int(summary.get("totalMatching", 0) or 0)
        if not results:
            return

        query = parse_qs(urlparse(response.url).query)
        current_start = int(query.get("start_rank", ["1"])[0])
        next_start = current_start + len(results)
        if next_start <= total:
            yield self._make_request(self._build_api_url(start_rank=next_start), callback=self.parse_api_list)

    def parse_course_list(self, response):
        links = response.css(f"{self.course_link_selector}::attr(href)").getall()
        if not links:
            # Fallback selectors for markup variations.
            links = response.css("a[href*='/study/course-finder/']::attr(href)").getall()
        if not links:
            links = response.css("a[href*='/study/courses/']::attr(href)").getall()
        if not links:
            # Some LSBU pages inject result URLs via JS payload rather than anchor tags.
            links = re.findall(
                r"(?:https?://www\.lsbu\.ac\.uk)?(/study/course-finder/[a-z0-9\-_/]+)",
                response.text,
                flags=re.IGNORECASE,
            )
        self.logger.info(f"[LSBU] Found {len(links)} links on {response.url}")

        for href in links:
            if href.startswith(("tel:", "mailto:", "javascript:")):
                continue

            url = response.urljoin(href)
            if "/study/course-finder/" not in url:
                continue
            if "/study/course-finder?" in url:
                continue
            if url.rstrip("/") == response.url.rstrip("/"):
                continue

            yield self._make_request(url, callback=self.parse_course)

        yield from self._follow_pagination(response, callback=self.parse_course_list)

    def parse_course(self, response):
        item = self._extract_and_normalise(response)
        if item:
            yield item
