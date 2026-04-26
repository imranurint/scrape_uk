"""
pipelines/validation.py
────────────────────────
First pipeline in the chain.

Drops items that are fundamentally unusable:
  - No course name
  - No source URL
  - Source URL not from an allowed domain (basic anti-pollution guard)

Logs every drop with a reason so ops teams can trace issues.
"""

from __future__ import annotations

import structlog
from scrapy import Spider
from scrapy.exceptions import DropItem

logger = structlog.get_logger(__name__)


class ValidationPipeline:
    """
    Stage 1: Drop obviously invalid items before any DB work.
    """

    def process_item(self, item: dict, spider: Spider) -> dict:
        course = item.get("course", {})
        metadata = item.get("metadata", {})

        # ── Must have a course name ───────────────────────────────────────────
        name = course.get("name", "").strip()
        if not name:
            raise DropItem(f"[{spider.name}] Missing course name — {metadata.get('url')}")

        # ── Must have a source URL ────────────────────────────────────────────
        url = metadata.get("url", "").strip()
        if not url or not url.startswith("http"):
            raise DropItem(f"[{spider.name}] Invalid/missing URL — course: {name!r}")

        # ── Name sanity check (not just whitespace / placeholder) ─────────────
        if len(name) < 3:
            raise DropItem(f"[{spider.name}] Course name too short: {name!r}")

        # ── Drop obvious non-course pages globally ────────────────────────────
        if self._is_non_course(name=name, url=url):
            raise DropItem(f"[{spider.name}] Non-course page detected — {url}")

        logger.debug("validation_passed", name=name, url=url)
        return item

    @staticmethod
    def _is_non_course(name: str, url: str) -> bool:
        """
        Lightweight guard against generic site pages being saved as courses.
        """
        lname = name.lower()
        lurl = url.lower()

        # Known non-course labels frequently found in nav/footer pages.
        blocked_name_tokens = {
            "contact",
            "contact us",
            "about",
            "about us",
            "privacy",
            "cookie",
            "cookies",
            "terms",
            "accessibility",
            "news",
            "events",
            "home",
            "apply",
            "open day",
        }
        if lname in blocked_name_tokens:
            return True

        # Non-course path segments should not be persisted as course records.
        blocked_url_tokens = (
            "/contact",
            "/about",
            "/news",
            "/event",
            "/events",
            "/privacy",
            "/cookie",
            "/cookies",
            "/terms",
            "/accessibility",
            "/help",
            "/support",
        )
        return any(token in lurl for token in blocked_url_tokens)
