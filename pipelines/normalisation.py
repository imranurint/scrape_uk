"""
pipelines/normalisation.py
───────────────────────────
Stage 2: Triggered if _needs_ai flag is set on an item.

When BeautifulSoup extracted too few fields (threshold set in Normalizer),
this pipeline calls AIExtractor to fill gaps — then merges results back.

If AI extraction is disabled (USE_AI_EXTRACTOR=false), this is a no-op.
"""

from __future__ import annotations

import asyncio

import structlog
from scrapy import Spider

from core.ai_extractor import AIExtractor

logger = structlog.get_logger(__name__)

_ai_extractor = AIExtractor()   # singleton — shares one aiohttp session


class NormalisationPipeline:
    """
    Stage 2: AI fallback enrichment for poorly-structured pages.

    If _needs_ai is False (most items), this pipeline does nothing and is
    essentially zero-cost — just a dict key check.
    """

    async def process_item(self, item: dict, spider: Spider) -> dict:
        if not item.pop("_needs_ai", False):
            # Clean up temp keys and pass through
            item.pop("_raw_description", None)
            item.pop("_raw_entry_req", None)
            return item

        url = item.get("metadata", {}).get("url", "")
        logger.info("ai_fallback_triggered", url=url)

        ai_data = await _ai_extractor.extract(url)
        if ai_data:
            self._merge_ai_data(item, ai_data)

        # Clean up temp keys
        item.pop("_raw_description", None)
        item.pop("_raw_entry_req", None)
        return item

    @staticmethod
    def _merge_ai_data(item: dict, ai_data: dict) -> None:
        """
        Fill in None fields from AI extraction result without overwriting
        already-populated fields.
        """
        course = item.setdefault("course", {})
        fees = item.setdefault("fees", {})
        admission = item.setdefault("admission", {})

        _fill_if_none(course, "name", ai_data.get("name"))
        _fill_if_none(course, "degree", ai_data.get("degree"))
        _fill_if_none(course, "department", ai_data.get("department"))
        _fill_if_none(course, "duration_years", ai_data.get("duration_years"))
        _fill_if_none(course, "start_month", ai_data.get("start_month"))

        uk = fees.setdefault("uk", {})
        intl = fees.setdefault("international", {})
        _fill_if_none(uk, "yearly", ai_data.get("fee_uk_yearly"))
        _fill_if_none(intl, "yearly", ai_data.get("fee_intl_yearly"))

        _fill_if_none(admission, "ucas_code", ai_data.get("ucas_code"))
        _fill_if_none(admission, "entry_requirements", ai_data.get("entry_requirements"))

        eng = admission.setdefault("english_requirement", {})
        _fill_if_none(eng, "ielts", ai_data.get("ielts_score"))

        logger.info("ai_merge_complete", url=item.get("metadata", {}).get("url"))


def _fill_if_none(d: dict, key: str, value) -> None:
    """Set dict[key] = value only if current value is None/missing."""
    if d.get(key) is None and value is not None:
        d[key] = value
