"""
core/normalizer.py
──────────────────
Maps a raw extraction dict (from BS4 or Crawl4AI) into a validated CourseSchema.

Responsibilities:
  - Clean / strip whitespace
  - Normalise degree strings ("BSc (Hons)" → "BSc")
  - Normalise level ("UG" → "undergraduate")
  - Sanitise fee values (remove commas, currency symbols)
  - Build the nested CourseSchema Pydantic model
  - Decide whether to fall back to AIExtractor if too many None fields
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

from models.schemas import (
    AdmissionSchema,
    ApplicationDeadlineSchema,
    CourseInfoSchema,
    CourseSchema,
    EnglishRequirementSchema,
    FeeDetailSchema,
    FeesSchema,
    MetadataSchema,
    UniversitySchema,
)

logger = structlog.get_logger(__name__)

# Threshold: if more than this many core fields are None, flag for AI fallback
AI_FALLBACK_THRESHOLD = 4

DEGREE_NORMALISATION = {
    "bsc": "BSc", "b.sc": "BSc",
    "ba": "BA", "b.a": "BA",
    "beng": "BEng", "b.eng": "BEng",
    "msc": "MSc", "m.sc": "MSc",
    "mres": "MRes",
    "mphil": "MPhil",
    "meng": "MEng",
    "mba": "MBA",
    "phd": "PhD", "ph.d": "PhD", "dphil": "DPhil",
    "llb": "LLB", "llm": "LLM",
    "mbchb": "MBChB", "bds": "BDS",
}

LEVEL_NORMALISATION = {
    "ug": "undergraduate", "undergraduate": "undergraduate",
    "pg": "postgraduate", "postgraduate": "postgraduate",
    "masters": "postgraduate",
    "research": "research", "doctoral": "research",
}


class Normalizer:
    """
    Converts a raw dict from CourseExtractor into a validated CourseSchema.

    Usage:
        norm = Normalizer(
            raw=extractor.extract(),
            university_name="UCL",
            university_location="London",
            source_url="https://...",
        )
        schema = norm.normalise()        # → CourseSchema or None
        needs_ai = norm.needs_ai_fallback()
    """

    def __init__(
        self,
        raw: dict[str, Any],
        university_name: str,
        university_location: str,
        source_url: str,
    ) -> None:
        self.raw = raw
        self.university_name = university_name
        self.university_location = university_location
        self.source_url = source_url

    def normalise(self) -> Optional[CourseSchema]:
        name = self._clean_str(self.raw.get("name"))
        if not name:
            logger.warning("normaliser_skip_no_name", url=self.source_url)
            return None

        try:
            return CourseSchema(
                university=UniversitySchema(
                    name=self.university_name,
                    location=self.university_location,
                ),
                course=CourseInfoSchema(
                    name=name,
                    degree=self._normalise_degree(self.raw.get("degree")),
                    level=self._normalise_level(self.raw.get("level")),
                    department=self._clean_str(self.raw.get("department")),
                    study_mode=self._normalise_study_modes(self.raw.get("study_mode")),
                    duration_years=self._to_float(self.raw.get("duration_years")),
                    start_month=self._clean_str(self.raw.get("start_month")),
                ),
                fees=FeesSchema(
                    uk=FeeDetailSchema(
                        yearly=self._to_int(self.raw.get("fee_uk_yearly")),
                        sandwich_year=self._to_int(self.raw.get("fee_uk_sandwich")),
                    ),
                    international=FeeDetailSchema(
                        yearly=self._to_int(self.raw.get("fee_intl_yearly")),
                        sandwich_year=self._to_int(self.raw.get("fee_intl_sandwich")),
                    ),
                ),
                admission=AdmissionSchema(
                    ucas_code=self._clean_str(self.raw.get("ucas_code")),
                    application_deadline=ApplicationDeadlineSchema(
                        main=self._clean_str(self.raw.get("deadline_main")),
                        late=self._clean_str(self.raw.get("deadline_late")),
                    ),
                    entry_requirements=self._clean_str(self.raw.get("entry_requirements")),
                    english_requirement=EnglishRequirementSchema(
                        ielts=self._to_float(self.raw.get("ielts_score")),
                    ),
                ),
                metadata=MetadataSchema(
                    url=self.source_url,
                    scraped_at=datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception as exc:
            logger.error("normaliser_build_failed", url=self.source_url, error=str(exc))
            return None

    def needs_ai_fallback(self) -> bool:
        """Returns True if too many core fields are missing."""
        core_fields = [
            "name", "degree", "fee_uk_yearly",
            "fee_intl_yearly", "entry_requirements", "description",
        ]
        missing = sum(1 for f in core_fields if not self.raw.get(f))
        return missing >= AI_FALLBACK_THRESHOLD

    # ─── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _clean_str(val: Any) -> Optional[str]:
        if not val:
            return None
        cleaned = re.sub(r"\s+", " ", str(val)).strip()
        return cleaned or None

    @staticmethod
    def _to_int(val: Any) -> Optional[int]:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        cleaned = re.sub(r"[^\d]", "", str(val))
        return int(cleaned) if cleaned else None

    @staticmethod
    def _to_float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalise_degree(raw: Any) -> Optional[str]:
        if not raw:
            return None
        key = re.sub(r"[\s\.\(\)Hons]+", "", str(raw)).lower()
        for k, v in DEGREE_NORMALISATION.items():
            if k in key:
                return v
        return str(raw).strip()[:20]

    @staticmethod
    def _normalise_level(raw: Any) -> Optional[str]:
        if not raw:
            return None
        key = str(raw).lower().strip()
        return LEVEL_NORMALISATION.get(key, key)

    @staticmethod
    def _normalise_study_modes(raw: Any) -> list[str]:
        if not raw:
            return ["full-time"]
        if isinstance(raw, list):
            return raw
        modes = []
        text = str(raw).lower()
        if "full" in text:
            modes.append("full-time")
        if "part" in text:
            modes.append("part-time")
        if "distance" in text:
            modes.append("distance-learning")
        return modes or ["full-time"]
