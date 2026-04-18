"""
tests/test_normalizer.py
─────────────────────────
Unit tests for Normalizer — verifies that raw dicts are correctly
transformed into valid CourseSchema objects.
"""

from __future__ import annotations

import pytest
from core.normalizer import Normalizer
from models.schemas import CourseSchema


FULL_RAW = {
    "name": "BSc (Hons) Computer Science",
    "degree": "BSc",
    "level": "undergraduate",
    "department": "Department of Computer Science",
    "ucas_code": "G400",
    "study_mode": ["full-time"],
    "duration_years": 3.0,
    "start_month": "September",
    "fee_uk_yearly": 9250,
    "fee_uk_sandwich": None,
    "fee_intl_yearly": 35000,
    "fee_intl_sandwich": None,
    "deadline_main": "15 January 2026",
    "deadline_late": None,
    "ielts_score": 6.5,
    "description": "A great course.",
    "entry_requirements": "AAA at A-level including Maths.",
}

SPARSE_RAW = {
    "name": "MSc Data Science",
    "degree": None,
    "level": None,
    "department": None,
    "ucas_code": None,
    "study_mode": None,
    "duration_years": None,
    "start_month": None,
    "fee_uk_yearly": None,
    "fee_uk_sandwich": None,
    "fee_intl_yearly": None,
    "fee_intl_sandwich": None,
    "deadline_main": None,
    "deadline_late": None,
    "ielts_score": None,
    "description": None,
    "entry_requirements": None,
}


class TestNormalizer:

    def _make(self, raw: dict) -> Normalizer:
        return Normalizer(
            raw=raw,
            university_name="UCL",
            university_location="London",
            source_url="https://ucl.ac.uk/test-course",
        )

    def test_normalise_returns_course_schema(self):
        schema = self._make(FULL_RAW).normalise()
        assert isinstance(schema, CourseSchema)

    def test_university_fields(self):
        schema = self._make(FULL_RAW).normalise()
        assert schema.university.name == "UCL"
        assert schema.university.location == "London"

    def test_course_name_cleaned(self):
        schema = self._make(FULL_RAW).normalise()
        assert schema.course.name == "BSc (Hons) Computer Science"

    def test_degree_normalised(self):
        raw = {**FULL_RAW, "degree": "bsc (hons)"}
        schema = self._make(raw).normalise()
        assert schema.course.degree == "BSc"

    def test_level_normalised(self):
        raw = {**FULL_RAW, "level": "ug"}
        schema = self._make(raw).normalise()
        assert schema.course.level == "undergraduate"

    def test_fees_populated(self):
        schema = self._make(FULL_RAW).normalise()
        assert schema.fees.uk.yearly == 9250
        assert schema.fees.international.yearly == 35000
        assert schema.fees.uk.currency == "GBP"

    def test_ielts_score(self):
        schema = self._make(FULL_RAW).normalise()
        assert schema.admission.english_requirement.ielts == 6.5

    def test_ucas_code(self):
        schema = self._make(FULL_RAW).normalise()
        assert schema.admission.ucas_code == "G400"

    def test_metadata_url(self):
        schema = self._make(FULL_RAW).normalise()
        assert schema.metadata.url == "https://ucl.ac.uk/test-course"

    def test_metadata_scraped_at_is_iso(self):
        schema = self._make(FULL_RAW).normalise()
        assert "T" in schema.metadata.scraped_at   # ISO 8601 format

    def test_sparse_raw_still_normalises(self):
        """Sparse input with only a name should still return a schema (not None)."""
        schema = self._make(SPARSE_RAW).normalise()
        assert schema is not None
        assert schema.course.name == "MSc Data Science"

    def test_empty_name_returns_none(self):
        raw = {**FULL_RAW, "name": ""}
        schema = self._make(raw).normalise()
        assert schema is None

    def test_needs_ai_fallback_sparse(self):
        norm = self._make(SPARSE_RAW)
        norm.normalise()
        assert norm.needs_ai_fallback() is True

    def test_needs_ai_fallback_full(self):
        norm = self._make(FULL_RAW)
        norm.normalise()
        assert norm.needs_ai_fallback() is False

    def test_study_mode_defaults_to_full_time(self):
        schema = self._make(SPARSE_RAW).normalise()
        assert schema.course.study_mode == ["full-time"]

    def test_fee_string_with_commas_parsed(self):
        raw = {**FULL_RAW, "fee_uk_yearly": "9,250"}
        schema = self._make(raw).normalise()
        assert schema.fees.uk.yearly == 9250
