"""
core/extractor.py
─────────────────
BeautifulSoup-based field extractor.

Strategy:
  Each university's page layout differs, so every extract_* helper tries a
  list of CSS selectors in priority order, returning the first match.
  This makes the extractor resilient to minor HTML changes without touching spider code.

Usage:
    from core.extractor import CourseExtractor
    ex = CourseExtractor(html_content, base_url="https://www.ucl.ac.uk/...")
    raw = ex.extract()   # → dict
"""

from __future__ import annotations

import re
from typing import Any, Optional

import structlog
from bs4 import BeautifulSoup, Tag

logger = structlog.get_logger(__name__)


class CourseExtractor:
    """
    Extracts structured course fields from raw HTML using BeautifulSoup.

    All public methods return None (not raise) on failure so the pipeline
    can decide whether to fall back to Crawl4AI or discard the item.
    """

    def __init__(self, html: str, base_url: str = "") -> None:
        self.soup = BeautifulSoup(html, "lxml")
        self.base_url = base_url

    # ─── Public API ───────────────────────────────────────────────────────────

    def extract(self) -> dict[str, Any]:
        """Return a flat dict of all extractable fields."""
        # Pre-extract meta tags for efficiency
        self.meta = self._extract_meta_tags()
        
        return {
            "name": self.extract_course_name(),
            "degree": self.extract_degree(),
            "level": self.extract_level(),
            "department": self.extract_department(),
            "ucas_code": self.extract_ucas_code(),
            "study_mode": self.extract_study_mode(),
            "duration_years": self.extract_duration(),
            "start_month": self.extract_start_month(),
            "fee_uk_yearly": self.extract_fee_uk(),
            "fee_uk_sandwich": self.extract_fee_uk_sandwich(),
            "fee_intl_yearly": self.extract_fee_international(),
            "fee_intl_sandwich": self.extract_fee_intl_sandwich(),
            "deadline_main": self.extract_deadline_main(),
            "deadline_late": self.extract_deadline_late(),
            "ielts_score": self.extract_ielts(),
            "description": self.extract_description(),
            "entry_requirements": self.extract_entry_requirements(),
        }

    # ─── Field extractors ─────────────────────────────────────────────────────

    def extract_course_name(self) -> Optional[str]:
        # Try meta tags first
        if name := (self.meta.get("og:title") or self.meta.get("twitter:title")):
            return name.split("|")[0].strip()

        selectors = [
            "h1.course-title",
            "h1[class*='course']",
            "h1[class*='title']",
            "#course-name",
            ".programme-header h1",
            "h1",
        ]
        return self._first_text(selectors)

    def extract_degree(self) -> Optional[str]:
        """Parse degree type from page — BSc, MSc, BA, PhD, etc."""
        text = self._first_text([
            ".course-type", ".qualification", "[class*='award']",
            ".degree-type", ".programme-type",
        ])
        if text:
            return self._parse_degree(text)
        # Fall back: look for degree in page title
        title = self.soup.find("title")
        if title:
            return self._parse_degree(title.get_text())
        return None

    def extract_level(self) -> Optional[str]:
        """undergraduate / postgraduate / research"""
        text_pool = " ".join([
            self._first_text(
                [".study-level", ".programme-level", "[class*='level']"]
            ) or "",
            (self.soup.find("title") or Tag()).get_text(),
        ]).lower()
        if "postgraduate" in text_pool or "masters" in text_pool or "msc" in text_pool:
            return "postgraduate"
        if "undergraduate" in text_pool or "bsc" in text_pool or "ba " in text_pool:
            return "undergraduate"
        if "phd" in text_pool or "doctorate" in text_pool or "research" in text_pool:
            return "research"
        return None

    def extract_department(self) -> Optional[str]:
        return self._first_text([
            ".department", ".faculty", "[class*='department']",
            "[class*='faculty']", ".school-name", "[class*='school']",
        ])

    def extract_ucas_code(self) -> Optional[str]:
        # Try meta tags
        if code := self.meta.get("programme:ucas_code"):
            return code

        # UCAS codes are 4-char alphanumeric: e.g. G100, F305
        text = self._first_text([
            ".ucas-code", "[class*='ucas']", "[data-ucas]", "dt:contains('UCAS') + dd",
        ])
        if text:
            match = re.search(r"\b([A-Z]\d{3})\b", text)
            if match:
                return match.group(1)
        # Brute-force scan all text
        for tag in self.soup.find_all(string=re.compile(r"\bUCAS\b", re.I)):
            m = re.search(r"\b([A-Z]\d{3})\b", str(tag.parent.get_text()))
            if m:
                return m.group(1)
        return None

    def extract_study_mode(self) -> list[str]:
        text = self._first_text([
            ".study-mode", "[class*='study-mode']", "[class*='mode-of-study']",
        ]) or ""
        modes = []
        if re.search(r"full[\s-]time", text, re.I):
            modes.append("full-time")
        if re.search(r"part[\s-]time", text, re.I):
            modes.append("part-time")
        if re.search(r"distance", text, re.I):
            modes.append("distance-learning")
        return modes or ["full-time"]  # sensible default

    def extract_duration(self) -> Optional[float]:
        # Try meta tags
        if dur_text := self.meta.get("programme:duration"):
            yr_match = re.search(r"(\d+)\s*academic\s*years", dur_text, re.I)
            if yr_match:
                return float(yr_match.group(1))

        text = self._first_text([
            ".duration", "[class*='duration']", "[class*='length']",
            "dt:contains('Duration') + dd", "dt:contains('Length') + dd",
        ]) or ""
        # Match patterns: "3 years", "4-year", "18 months"
        yr_match = re.search(r"(\d+\.?\d*)\s*year", text, re.I)
        if yr_match:
            return float(yr_match.group(1))
        mo_match = re.search(r"(\d+)\s*month", text, re.I)
        if mo_match:
            return round(int(mo_match.group(1)) / 12, 1)
        return None

    def extract_start_month(self) -> Optional[str]:
        months = (
            "January|February|March|April|May|June|"
            "July|August|September|October|November|December"
        )
        text = self._first_text([
            "[class*='start']", "[class*='intake']", "dt:contains('Start') + dd",
        ]) or ""
        match = re.search(months, text, re.I)
        return match.group(0).capitalize() if match else None

    def extract_fee_uk(self) -> Optional[int]:
        return self._extract_fee(["uk", "home", "domestic", "home/eu"])

    def extract_fee_uk_sandwich(self) -> Optional[int]:
        return self._extract_fee(["sandwich", "placement year"], context="uk")

    def extract_fee_international(self) -> Optional[int]:
        return self._extract_fee(["international", "overseas", "intl"])

    def extract_fee_intl_sandwich(self) -> Optional[int]:
        return self._extract_fee(["sandwich", "placement year"], context="international")

    def extract_deadline_main(self) -> Optional[str]:
        text = self._first_text([
            "[class*='deadline']", "[class*='closing']",
            "dt:contains('Application') + dd", "dt:contains('Deadline') + dd",
        ])
        return text.strip() if text else None

    def extract_deadline_late(self) -> Optional[str]:
        # Look for "late" or "clearing" deadline specifically
        for tag in self.soup.find_all(string=re.compile(r"late|clearing", re.I)):
            parent_text = tag.parent.get_text(strip=True)
            if re.search(r"\d{4}", parent_text):  # contains a year
                return parent_text[:100]
        return None

    def extract_ielts(self) -> Optional[float]:
        text = ""
        for tag in self.soup.find_all(string=re.compile(r"IELTS", re.I)):
            text += " " + tag.parent.get_text()
        match = re.search(r"IELTS[^\d]*(\d+\.?\d*)", text, re.I)
        if match:
            return float(match.group(1))
        return None

    def extract_description(self) -> Optional[str]:
        selectors = [
            ".course-description", ".course-overview", "#overview",
            "[class*='description']", "[class*='overview']", ".intro-text",
        ]
        return self._first_text(selectors, strip_length=5000)

    def extract_entry_requirements(self) -> Optional[str]:
        selectors = [
            "#entry-requirements", ".entry-requirements",
            "[class*='entry-req']", "[class*='requirements']",
            "section:has(h2:contains('Entry'))",
        ]
        return self._first_text(selectors, strip_length=3000)

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _first_text(
        self, selectors: list[str], strip_length: int = 500
    ) -> Optional[str]:
        """Try each CSS selector; return first non-empty text found."""
        for sel in selectors:
            try:
                el = self.soup.select_one(sel)
                if el:
                    text = el.get_text(separator=" ", strip=True)
                    if text:
                        return text[:strip_length]
            except Exception:
                continue
        return None

    def _extract_fee(
        self, keywords: list[str], context: str = ""
    ) -> Optional[int]:
        """
        Find a £ amount near one of the keyword labels.
        Scans all text nodes, picks the closest monetary value.
        """
        text = self.soup.get_text(separator="\n")
        for kw in keywords:
            pattern = rf"(?i){re.escape(kw)}[^\n£]*£\s*([\d,]+)"
            match = re.search(pattern, text)
            if match:
                return int(match.group(1).replace(",", ""))
        # Generic £ amount scan as last resort
        matches = re.findall(r"£\s*([\d,]+)", text)
        if matches:
            return int(matches[0].replace(",", ""))
        return None

    def _extract_meta_tags(self) -> dict[str, str]:
        """Extract all <meta> tags into a dictionary."""
        meta = {}
        # Support both 'name' and 'property' (og tags)
        for tag in self.soup.find_all("meta"):
            key = tag.get("name") or tag.get("property")
            if key and tag.get("content"):
                meta[key] = tag["content"].strip()
        return meta

    @staticmethod
    def _parse_degree(text: str) -> Optional[str]:
        """Extract degree abbreviation from arbitrary text."""
        known = [
            "PhD", "DPhil", "MSc", "MRes", "MBA", "MEng", "MPhil",
            "MA ", "BSc", "BEng", "BA ", "BBA", "LLB", "LLM",
            "MBChB", "BDS", "MArch",
        ]
        for deg in known:
            if deg.lower() in text.lower():
                return deg.strip()
        return None
