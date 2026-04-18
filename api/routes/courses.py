"""
api/routes/courses.py
──────────────────────
Course endpoints:

  GET /courses/search          — full-text + filter search
  GET /courses/{id}            — single course as full CourseSchema JSON
  GET /courses/{id}/raw        — raw DB row (debug)

Query params for /courses/search:
  q           — keyword search (name + department, uses PG full-text)
  university  — filter by university name (partial, case-insensitive)
  degree      — filter by degree type (BSc, MSc, …)
  level       — undergraduate / postgraduate / research
  min_fee     — UK yearly fee ≥ value
  max_fee     — UK yearly fee ≤ value
  page        — page number (default 1)
  page_size   — results per page (default 20, max 100)
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.database import get_db
from models.db import Course, University
from models.schemas import CourseListItem, CourseSchema, PaginatedCourses

logger = structlog.get_logger(__name__)
router = APIRouter()


# ─── Search / Filter ──────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=PaginatedCourses,
    summary="Search and filter courses",
)
async def search_courses(
    q: Optional[str] = Query(None, description="Keyword search (name, department)"),
    university: Optional[str] = Query(None, description="Filter by university name"),
    degree: Optional[str] = Query(None, description="Filter by degree type, e.g. BSc"),
    level: Optional[str] = Query(None, description="undergraduate | postgraduate | research"),
    min_fee: Optional[int] = Query(None, description="Min UK yearly fee (GBP)"),
    max_fee: Optional[int] = Query(None, description="Max UK yearly fee (GBP)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCourses:

    stmt = (
        select(Course, University.name.label("uni_name"), University.location.label("uni_location"))
        .join(University, Course.university_id == University.id)
        .where(Course.is_active.is_(True))
    )

    # ── Full-text keyword search ──────────────────────────────────────────────
    if q:
        # Use PostgreSQL plainto_tsquery for safe, fast FTS
        # Falls back to ILIKE if search_vector is not yet populated
        fts_condition = Course.search_vector.op("@@")(func.plainto_tsquery("english", q))
        ilike_condition = or_(
            Course.name.ilike(f"%{q}%"),
            Course.department.ilike(f"%{q}%"),
        )
        stmt = stmt.where(or_(fts_condition, ilike_condition))

    # ── Filters ───────────────────────────────────────────────────────────────
    if university:
        stmt = stmt.where(University.name.ilike(f"%{university}%"))
    if degree:
        stmt = stmt.where(Course.degree.ilike(f"%{degree}%"))
    if level:
        stmt = stmt.where(Course.level.ilike(f"%{level}%"))
    if min_fee is not None:
        stmt = stmt.where(Course.fee_uk_yearly >= min_fee)
    if max_fee is not None:
        stmt = stmt.where(Course.fee_uk_yearly <= max_fee)

    # ── Count total ───────────────────────────────────────────────────────────
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # ── Paginate ──────────────────────────────────────────────────────────────
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Course.name).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).all()

    results = [
        CourseListItem(
            id=str(row.Course.id),
            name=row.Course.name,
            degree=row.Course.degree,
            level=row.Course.level,
            department=row.Course.department,
            university_name=row.uni_name,
            university_location=row.uni_location,
            duration_years=float(row.Course.duration_years) if row.Course.duration_years else None,
            fee_uk_yearly=row.Course.fee_uk_yearly,
            fee_intl_yearly=row.Course.fee_intl_yearly,
            source_url=row.Course.source_url,
        )
        for row in rows
    ]

    return PaginatedCourses(total=total, page=page, page_size=page_size, results=results)


# ─── Single Course (Full Schema) ──────────────────────────────────────────────

@router.get(
    "/{course_id}",
    response_model=CourseSchema,
    summary="Get full course details",
)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CourseSchema:

    stmt = (
        select(Course)
        .options(
            selectinload(Course.university),
            selectinload(Course.details),
        )
        .where(Course.id == course_id)
    )
    course = (await db.execute(stmt)).scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    return _course_to_schema(course)


# ─── Mapper: ORM → CourseSchema ───────────────────────────────────────────────

def _course_to_schema(c: Course) -> CourseSchema:
    """Convert ORM Course (with relations loaded) to the canonical output schema."""
    from models.schemas import (
        AdmissionSchema, ApplicationDeadlineSchema, CourseInfoSchema,
        CourseSchema, EnglishRequirementSchema, FeeDetailSchema,
        FeesSchema, MetadataSchema, UniversitySchema,
    )
    from datetime import timezone

    study_modes = (c.study_mode or "full-time").split(",")

    return CourseSchema(
        university=UniversitySchema(
            name=c.university.name if c.university else "Unknown",
            location=c.university.location if c.university else None,
        ),
        course=CourseInfoSchema(
            name=c.name,
            degree=c.degree,
            level=c.level,
            department=c.department,
            study_mode=study_modes,
            duration_years=float(c.duration_years) if c.duration_years else None,
            start_month=c.start_month,
        ),
        fees=FeesSchema(
            uk=FeeDetailSchema(yearly=c.fee_uk_yearly, sandwich_year=c.fee_uk_sandwich),
            international=FeeDetailSchema(yearly=c.fee_intl_yearly, sandwich_year=c.fee_intl_sandwich),
        ),
        admission=AdmissionSchema(
            ucas_code=c.ucas_code,
            application_deadline=ApplicationDeadlineSchema(
                main=c.deadline_main, late=c.deadline_late
            ),
            entry_requirements=c.details.entry_requirements if c.details else None,
            english_requirement=EnglishRequirementSchema(
                ielts=float(c.ielts_score) if c.ielts_score else None
            ),
        ),
        metadata=MetadataSchema(
            url=c.source_url,
            scraped_at=c.scraped_at.isoformat() if c.scraped_at else "",
        ),
    )
