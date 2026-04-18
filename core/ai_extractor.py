"""
core/ai_extractor.py
─────────────────────
Optional Crawl4AI-based extractor.

This module is only invoked when:
  1. USE_AI_EXTRACTOR=true in .env, AND
  2. The BS4 extractor returns too many None fields (poor HTML structure).

Strategy:
  Crawl4AI fetches the page, converts it to clean markdown, then we either:
    a) Parse structured fields from markdown with regex (fast, free), OR
    b) Send markdown to an LLM to get JSON (slower, costs tokens).

  Mode (a) is the default. Mode (b) requires OPENAI_API_KEY.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# Guard import — Crawl4AI is optional
try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("crawl4ai not installed — AI extraction disabled")


# ─── Pydantic schema for LLM extraction ──────────────────────────────────────
# This is sent to the LLM as the target JSON structure.
LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "name":              {"type": "string"},
        "degree":            {"type": "string"},
        "department":        {"type": "string"},
        "duration_years":    {"type": "number"},
        "start_month":       {"type": "string"},
        "fee_uk_yearly":     {"type": "integer"},
        "fee_intl_yearly":   {"type": "integer"},
        "ucas_code":         {"type": "string"},
        "ielts_score":       {"type": "number"},
        "description":       {"type": "string"},
        "entry_requirements":{"type": "string"},
    },
}

LLM_INSTRUCTION = (
    "Extract the following fields from this UK university course page. "
    "Return ONLY valid JSON with the keys specified. "
    "Use null for any field you cannot find. "
    "Fees must be integers in GBP (no currency symbols). "
    "duration_years should be a decimal number (e.g. 3.0 or 1.5 for 18 months)."
)


class AIExtractor:
    """
    Uses Crawl4AI to render and extract content from a course URL.

    Usage:
        extractor = AIExtractor()
        data = await extractor.extract(url)
    """

    def __init__(self) -> None:
        self._enabled = (
            CRAWL4AI_AVAILABLE
            and os.getenv("USE_AI_EXTRACTOR", "false").lower() == "true"
        )
        self._use_llm = bool(os.getenv("OPENAI_API_KEY"))

    async def extract(self, url: str) -> Optional[dict[str, Any]]:
        """
        Main entry point.
        Returns a dict compatible with CourseExtractor.extract() output, or None.
        """
        if not self._enabled:
            return None

        try:
            if self._use_llm:
                return await self._extract_with_llm(url)
            else:
                markdown = await self._get_markdown(url)
                return self._parse_markdown(markdown) if markdown else None
        except Exception as exc:
            logger.error("ai_extraction_failed", url=url, error=str(exc))
            return None

    # ─── Mode A: markdown → regex ─────────────────────────────────────────────

    async def _get_markdown(self, url: str) -> Optional[str]:
        """Render page and return clean markdown."""
        config = CrawlerRunConfig(
            word_count_threshold=10,
            exclude_external_links=True,
            remove_overlay_elements=True,
        )
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, config=config)
        return result.markdown if result.success else None

    def _parse_markdown(self, md: str) -> dict[str, Any]:
        """
        Extract structured fields from markdown using regex.
        Good enough for ~80% of standard university pages.
        """
        import re

        def find(pattern: str, text: str = md) -> Optional[str]:
            m = re.search(pattern, text, re.I | re.MULTILINE)
            return m.group(1).strip() if m else None

        def find_int(pattern: str) -> Optional[int]:
            val = find(pattern)
            if val:
                cleaned = re.sub(r"[^\d]", "", val)
                return int(cleaned) if cleaned else None
            return None

        return {
            "name": find(r"^#\s+(.+)$"),
            "degree": find(r"\b(BSc|MSc|BA|BEng|MEng|MBA|PhD|MRes|MPhil)\b"),
            "department": find(r"(?:Department|School|Faculty)\s+of\s+([^\n]+)"),
            "duration_years": self._parse_duration(find(r"(\d+\.?\d*\s*(?:year|yr)s?)") or ""),
            "start_month": find(r"Start(?:s|ing)?\s*(?:date)?:?\s*(\w+)"),
            "fee_uk_yearly": find_int(r"UK.*?£\s*([\d,]+)"),
            "fee_intl_yearly": find_int(r"International.*?£\s*([\d,]+)"),
            "ucas_code": find(r"\b([A-Z]\d{3})\b"),
            "ielts_score": float(find(r"IELTS[^\d]*(\d+\.?\d*)") or 0) or None,
            "description": md[:2000] if md else None,
            "entry_requirements": find(r"Entry Requirements\s*\n([\s\S]{100,1500})"),
            "fee_uk_sandwich": None,
            "fee_intl_sandwich": None,
            "deadline_main": None,
            "deadline_late": None,
            "study_mode": ["full-time"],
        }

    # ─── Mode B: LLM extraction ───────────────────────────────────────────────

    async def _extract_with_llm(self, url: str) -> Optional[dict[str, Any]]:
        """Use Crawl4AI's LLMExtractionStrategy to get structured JSON."""
        strategy = LLMExtractionStrategy(
            provider="openai/gpt-4o-mini",   # cheap + accurate enough
            api_token=os.getenv("OPENAI_API_KEY"),
            schema=LLM_SCHEMA,
            extraction_type="schema",
            instruction=LLM_INSTRUCTION,
        )
        config = CrawlerRunConfig(
            extraction_strategy=strategy,
            word_count_threshold=10,
        )
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, config=config)

        if not result.success or not result.extracted_content:
            return None

        try:
            data = json.loads(result.extracted_content)
            # Ensure all expected keys present
            defaults = {
                "fee_uk_sandwich": None, "fee_intl_sandwich": None,
                "deadline_main": None, "deadline_late": None,
                "study_mode": ["full-time"], "level": None, "start_month": None,
            }
            return {**defaults, **data}
        except json.JSONDecodeError:
            logger.warning("llm_json_parse_failed", url=url)
            return None

    @staticmethod
    def _parse_duration(text: str) -> Optional[float]:
        import re
        m = re.search(r"(\d+\.?\d*)", text)
        return float(m.group(1)) if m else None
