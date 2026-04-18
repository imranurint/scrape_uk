"""
pipelines/duplicates.py
────────────────────────
Stage 3: In-memory deduplication by source URL.

URL is the natural dedup key — if we scrape the same course page twice
(e.g. from two different listing pages), we drop the second occurrence.

Note: this is a per-run cache. Cross-run dedup is handled by the
DatabasePipeline using PostgreSQL's ON CONFLICT DO UPDATE (upsert).
"""

from __future__ import annotations

import structlog
from scrapy import Spider
from scrapy.exceptions import DropItem

logger = structlog.get_logger(__name__)


class DuplicatesPipeline:
    """
    Stage 3: Per-crawl URL deduplication (O(1) set lookup).
    """

    def __init__(self) -> None:
        self._seen_urls: set[str] = set()

    def process_item(self, item: dict, spider: Spider) -> dict:
        url = item.get("metadata", {}).get("url", "")

        if url in self._seen_urls:
            logger.debug("duplicate_dropped", url=url)
            raise DropItem(f"Duplicate URL: {url}")

        self._seen_urls.add(url)
        return item

    def close_spider(self, spider: Spider) -> None:
        logger.info(
            "dedup_summary",
            spider=spider.name,
            total_unique_urls=len(self._seen_urls),
        )
