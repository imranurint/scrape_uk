"""
scrapers/base_spider.py
───────────────────────
Abstract base class for all UK university spiders.

Every university spider inherits from BaseUniversitySpider and implements:
  - start_urls
  - parse_course_list()   → yield Request objects to individual courses
  - parse_course()        → yield CourseItem dicts

The base class handles:
  - Playwright opt-in per request (needs_js flag)
  - Structured logging of all requests/responses
  - Centralised error handling
  - AI extractor fallback invocation
"""

from __future__ import annotations

import asyncio
from typing import Any, Generator, Iterator, Optional

import scrapy
import structlog
from scrapy import Spider
from scrapy.http import Response, Request

from core.extractor import CourseExtractor
from core.normalizer import Normalizer

logger = structlog.get_logger(__name__)


class BaseUniversitySpider(Spider):
    """
    Abstract spider. Subclasses MUST define:
        name              : str
        university_name   : str
        university_location: str
        start_urls        : list[str]
        needs_js          : bool  (True → use Playwright for detail pages)
    """

    # ── Subclass must override ────────────────────────────────────────────────
    university_name: str = ""
    university_location: str = ""
    needs_js: bool = False              # per-spider flag

    # ── Playwright page-wait selector (override if needed) ────────────────────
    wait_for_selector: Optional[str] = None

    # ── Optional CSS hint for course detail links on list pages ───────────────
    course_link_selector: str = "a[href]"     # override per spider
    next_page_selector: str = ""              # CSS for pagination "next" button

    # ─────────────────────────────────────────────────────────────────────────

    custom_settings: dict[str, Any] = {}     # spider-level Scrapy overrides

    def start_requests(self) -> Iterator[Request]:
        """Generate opening requests, optionally through Playwright."""
        for url in self.start_urls:
            yield self._make_request(url, callback=self.parse_course_list)

    # ── Must override ─────────────────────────────────────────────────────────

    def parse_course_list(self, response: Response) -> Generator:
        """
        Parse a course listing page.
        Should yield Request(s) to individual course pages.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement parse_course_list")

    def parse_course(self, response: Response) -> Generator:
        """
        Parse an individual course detail page.
        Should yield a dict (CourseItem).
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement parse_course")

    # ── Base utilities ────────────────────────────────────────────────────────

    def _make_request(
        self,
        url: str,
        callback,
        use_js: Optional[bool] = None,
        cb_kwargs: Optional[dict] = None,
    ) -> Request:
        """
        Build a Scrapy Request, enabling Playwright if needed.
        use_js defaults to the spider-level needs_js flag.
        """
        if use_js is None:
            use_js = self.needs_js

        meta: dict[str, Any] = {}

        if use_js:
            meta["playwright"] = True
            meta["playwright_include_page"] = False    # don't leak Page objects
            if self.wait_for_selector:
                from scrapy_playwright.page import PageMethod
                meta["playwright_page_methods"] = [
                    PageMethod("wait_for_selector", self.wait_for_selector, timeout=15_000),
                    PageMethod("wait_for_load_state", "networkidle"),
                ]

        return Request(
            url=url,
            callback=callback,
            meta=meta,
            cb_kwargs=cb_kwargs or {},
            errback=self._errback,
        )

    def _extract_and_normalise(
        self, response: Response
    ) -> Optional[dict[str, Any]]:
        """
        Run BS4 extraction → normalisation.
        Returns a flat dict ready for the pipeline, or None on failure.
        """
        try:
            extractor = CourseExtractor(response.text, base_url=response.url)
            raw = extractor.extract()

            norm = Normalizer(
                raw=raw,
                university_name=self.university_name,
                university_location=self.university_location,
                source_url=response.url,
            )

            schema = norm.normalise()
            if schema is None:
                logger.warning("extraction_returned_none", url=response.url)
                return None

            # Mark if AI fallback is desired (pipeline will handle it)
            result = schema.model_dump()
            result["_needs_ai"] = norm.needs_ai_fallback()
            result["_raw_description"] = raw.get("description")
            result["_raw_entry_req"] = raw.get("entry_requirements")
            return result

        except Exception as exc:
            logger.error("extraction_failed", url=response.url, error=str(exc))
            return None

    def _follow_pagination(
        self, response: Response, callback
    ) -> Generator[Request, None, None]:
        """Follow `next page` links using spider's next_page_selector."""
        if not self.next_page_selector:
            return
        next_url = response.css(f"{self.next_page_selector}::attr(href)").get()
        if next_url:
            abs_url = response.urljoin(next_url)
            logger.info("following_next_page", url=abs_url)
            yield self._make_request(abs_url, callback=callback)

    def _errback(self, failure) -> None:
        """Log download errors without crashing the spider."""
        logger.error(
            "request_failed",
            url=failure.request.url,
            error=repr(failure.value),
        )
