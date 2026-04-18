"""
models/schemas.py
─────────────────
Pydantic v2 schemas.

CourseSchema matches the exact JSON output format specified in the brief.
These are used:
  - as FastAPI response models
  - as the authoritative shape for normalised scraper output
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ─── Sub-models ──────────────────────────────────────────────────────────────

class UniversitySchema(BaseModel):
    name: str
    location: Optional[str] = None


class CourseInfoSchema(BaseModel):
    name: str
    degree: Optional[str] = None          # BSc, MSc, PhD, BA …
    level: Optional[str] = None           # undergraduate / postgraduate
    department: Optional[str] = None
    study_mode: list[str] = Field(default_factory=list)
    duration_years: Optional[float] = None
    start_month: Optional[str] = None


class FeeDetailSchema(BaseModel):
    yearly: Optional[int] = None
    sandwich_year: Optional[int] = None
    currency: str = "GBP"


class FeesSchema(BaseModel):
    uk: FeeDetailSchema = Field(default_factory=FeeDetailSchema)
    international: FeeDetailSchema = Field(default_factory=FeeDetailSchema)


class ApplicationDeadlineSchema(BaseModel):
    main: Optional[str] = None
    late: Optional[str] = None


class EnglishRequirementSchema(BaseModel):
    ielts: Optional[float] = None


class AdmissionSchema(BaseModel):
    ucas_code: Optional[str] = None
    application_deadline: ApplicationDeadlineSchema = Field(
        default_factory=ApplicationDeadlineSchema
    )
    entry_requirements: Optional[str] = None
    english_requirement: EnglishRequirementSchema = Field(
        default_factory=EnglishRequirementSchema
    )


class MetadataSchema(BaseModel):
    url: str
    scraped_at: str


# ─── Root schema (matches brief output format exactly) ───────────────────────

class CourseSchema(BaseModel):
    """
    The canonical output shape for a single scraped course.
    Returned by the API and produced by the normaliser.
    """

    university: UniversitySchema
    course: CourseInfoSchema
    fees: FeesSchema = Field(default_factory=FeesSchema)
    admission: AdmissionSchema = Field(default_factory=AdmissionSchema)
    metadata: MetadataSchema

    model_config = {"from_attributes": True}


# ─── API-specific schemas ────────────────────────────────────────────────────

class CourseListItem(BaseModel):
    """Lightweight row for list endpoints — avoids fetching details."""

    id: str
    name: str
    degree: Optional[str] = None
    level: Optional[str] = None
    department: Optional[str] = None
    university_name: str
    university_location: Optional[str] = None
    duration_years: Optional[float] = None
    fee_uk_yearly: Optional[int] = None
    fee_intl_yearly: Optional[int] = None
    source_url: str

    model_config = {"from_attributes": True}


class PaginatedCourses(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[CourseListItem]


class UniversityListItem(BaseModel):
    id: str
    name: str
    location: Optional[str] = None
    website: Optional[str] = None
    course_count: int = 0
