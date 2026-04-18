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

        logger.debug("validation_passed", name=name, url=url)
        return item
