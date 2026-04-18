"""
api/routes/universities.py
───────────────────────────
University endpoints:

  GET /universities          — list all universities with course counts
  GET /universities/{id}     — university detail with course summary
"""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from config.database import get_db
from models.db import Course, University
from models.schemas import UniversityListItem

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "",
    response_model=list[UniversityListItem],
    summary="List all universities with course counts",
)
async def list_universities(db=Depends(get_db)) -> list[UniversityListItem]:
    stmt = (
        select(
            University,
            func.count(Course.id).label("course_count"),
        )
        .outerjoin(Course, Course.university_id == University.id)
        .group_by(University.id)
        .order_by(University.name)
    )
    rows = (await db.execute(stmt)).all()

    return [
        UniversityListItem(
            id=str(row.University.id),
            name=row.University.name,
            location=row.University.location,
            website=row.University.website,
            course_count=row.course_count,
        )
        for row in rows
    ]


@router.get(
    "/{university_id}",
    response_model=UniversityListItem,
    summary="Get university by ID",
)
async def get_university(university_id: UUID, db=Depends(get_db)) -> UniversityListItem:
    stmt = (
        select(University, func.count(Course.id).label("course_count"))
        .outerjoin(Course, Course.university_id == University.id)
        .where(University.id == university_id)
        .group_by(University.id)
    )
    row = (await db.execute(stmt)).one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail=f"University {university_id} not found")

    return UniversityListItem(
        id=str(row.University.id),
        name=row.University.name,
        location=row.University.location,
        website=row.University.website,
        course_count=row.course_count,
    )
