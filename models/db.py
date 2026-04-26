"""
models/db.py
────────────
SQLAlchemy ORM models.

Schema:
  universities   — one row per institution
  courses        — one row per course (FK → universities)
  course_details — long-form text fields split out to keep courses table lean
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    Index,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


# ─── University ───────────────────────────────────────────────────────────────
class University(Base):
    __tablename__ = "universities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    website: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    courses: Mapped[list["Course"]] = relationship(back_populates="university")


# ─── Course ───────────────────────────────────────────────────────────────────
class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_courses_source_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("universities.id", ondelete="CASCADE")
    )

    # ── Core identifiers ─────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(50))   # BSc, MSc, PhD …
    level: Mapped[str | None] = mapped_column(String(50))    # undergraduate, postgraduate
    department: Mapped[str | None] = mapped_column(String(255))
    ucas_code: Mapped[str | None] = mapped_column(String(10))

    # ── Study details ─────────────────────────────────────────────────────────
    study_mode: Mapped[str | None] = mapped_column(String(100))   # "full-time,part-time"
    duration_years: Mapped[float | None] = mapped_column(Numeric(4, 1))
    start_month: Mapped[str | None] = mapped_column(String(20))

    # ── Fees (GBP) ────────────────────────────────────────────────────────────
    fee_uk_yearly: Mapped[int | None] = mapped_column(BigInteger)
    fee_uk_sandwich: Mapped[int | None] = mapped_column(BigInteger)
    fee_intl_yearly: Mapped[int | None] = mapped_column(BigInteger)
    fee_intl_sandwich: Mapped[int | None] = mapped_column(BigInteger)

    # ── Admissions ────────────────────────────────────────────────────────────
    deadline_main: Mapped[str | None] = mapped_column(String(50))
    deadline_late: Mapped[str | None] = mapped_column(String(50))
    ielts_score: Mapped[float | None] = mapped_column(Numeric(3, 1))

    # ── Metadata ─────────────────────────────────────────────────────────────
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Full-text search vector (populated by DB trigger in migration - disabled for SQLite)
    search_vector: Mapped[str | None] = mapped_column(String)
    raw_json: Mapped[str | None] = mapped_column(Text)   # Full JSON blob of the scraped item

    university: Mapped["University"] = relationship(back_populates="courses")
    details: Mapped["CourseDetail | None"] = relationship(
        back_populates="course", uselist=False
    )


# ─── Course Detail ────────────────────────────────────────────────────────────
class CourseDetail(Base):
    """Long-form text split from Course to keep main table narrow."""

    __tablename__ = "course_details"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(Text)
    entry_requirements: Mapped[str | None] = mapped_column(Text)
    modules: Mapped[str | None] = mapped_column(Text)   # JSON string of module list
    career_prospects: Mapped[str | None] = mapped_column(Text)

    course: Mapped["Course"] = relationship(back_populates="details")
