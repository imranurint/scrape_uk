"""
tests/test_extractor.py
────────────────────────
Unit tests for CourseExtractor — no network, no DB.
We feed in fixture HTML strings and verify field extraction.
"""

from __future__ import annotations

import pytest
from core.extractor import CourseExtractor


# ─── Fixtures ────────────────────────────────────────────────────────────────

SIMPLE_COURSE_HTML = """
<!DOCTYPE html>
<html>
<head><title>BSc Computer Science - UCL</title></head>
<body>
  <h1 class="course-title">BSc Computer Science</h1>
  <div class="department">Department of Computer Science</div>
  <div class="duration">3 years full-time</div>
  <div class="study-mode">Full-time, Part-time</div>
  <div class="ucas-code">UCAS Code: G400</div>
  <p>IELTS minimum score: 6.5 overall</p>
  <div class="course-description">
    This programme provides a thorough grounding in computer science fundamentals.
  </div>
  <div id="entry-requirements">
    A-levels: AAA including Mathematics.
    GCSE: Mathematics and English Language at grade C/4 or above.
  </div>
  <p>UK tuition fee: £9,250 per year</p>
  <p>International fee: £35,000 per year</p>
  <div class="start-date">The programme starts in September.</div>
</body>
</html>
"""

MINIMAL_HTML = """
<html><body><h1>Some Course</h1></body></html>
"""

FEE_ONLY_HTML = """
<html><body>
  <h1>MBA Finance</h1>
  <p>Home/UK students: £18,500</p>
  <p>International students: £28,000</p>
</body></html>
"""


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestCourseExtractor:

    def test_extracts_course_name(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML, base_url="https://ucl.ac.uk/test")
        assert ex.extract_course_name() == "BSc Computer Science"

    def test_extracts_degree_from_name(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        assert ex.extract_degree() == "BSc"

    def test_extracts_department(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        assert "Computer Science" in ex.extract_department()

    def test_extracts_duration_years(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        assert ex.extract_duration() == 3.0

    def test_extracts_study_modes(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        modes = ex.extract_study_mode()
        assert "full-time" in modes
        assert "part-time" in modes

    def test_extracts_ucas_code(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        assert ex.extract_ucas_code() == "G400"

    def test_extracts_ielts_score(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        assert ex.extract_ielts() == 6.5

    def test_extracts_uk_fee(self):
        ex = CourseExtractor(FEE_ONLY_HTML)
        fee = ex.extract_fee_uk()
        assert fee == 18500

    def test_extracts_international_fee(self):
        ex = CourseExtractor(FEE_ONLY_HTML)
        fee = ex.extract_fee_international()
        assert fee == 28000

    def test_extracts_start_month(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        assert ex.extract_start_month() == "September"

    def test_extract_returns_dict_with_all_keys(self):
        ex = CourseExtractor(SIMPLE_COURSE_HTML)
        result = ex.extract()
        expected_keys = {
            "name", "degree", "level", "department", "ucas_code",
            "study_mode", "duration_years", "start_month",
            "fee_uk_yearly", "fee_uk_sandwich", "fee_intl_yearly",
            "fee_intl_sandwich", "deadline_main", "deadline_late",
            "ielts_score", "description", "entry_requirements",
        }
        assert expected_keys.issubset(result.keys())

    def test_minimal_html_returns_name_only(self):
        ex = CourseExtractor(MINIMAL_HTML)
        assert ex.extract_course_name() == "Some Course"
        assert ex.extract_ucas_code() is None
        assert ex.extract_duration() is None

    def test_duration_in_months(self):
        html = "<html><body><h1>X</h1><div class='duration'>18 months</div></body></html>"
        ex = CourseExtractor(html)
        assert ex.extract_duration() == 1.5
