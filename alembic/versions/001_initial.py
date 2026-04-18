"""Initial schema — universities, courses, course_details

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── universities ─────────────────────────────────────────────────────────
    op.create_table(
        "universities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("location", sa.String(255)),
        sa.Column("website", sa.String(512)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # ── courses ───────────────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "university_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("universities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("degree", sa.String(50)),
        sa.Column("level", sa.String(50)),
        sa.Column("department", sa.String(255)),
        sa.Column("ucas_code", sa.String(10)),
        sa.Column("study_mode", sa.String(100)),
        sa.Column("duration_years", sa.Numeric(4, 1)),
        sa.Column("start_month", sa.String(20)),
        sa.Column("fee_uk_yearly", sa.BigInteger()),
        sa.Column("fee_uk_sandwich", sa.BigInteger()),
        sa.Column("fee_intl_yearly", sa.BigInteger()),
        sa.Column("fee_intl_sandwich", sa.BigInteger()),
        sa.Column("deadline_main", sa.String(50)),
        sa.Column("deadline_late", sa.String(50)),
        sa.Column("ielts_score", sa.Numeric(3, 1)),
        sa.Column("source_url", sa.String(1024), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
        ),
    )

    # GIN index for full-text search
    op.create_index(
        "ix_courses_fts",
        "courses",
        ["search_vector"],
        postgresql_using="gin",
    )

    # ── DB trigger: auto-update search_vector on insert/update ───────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION courses_search_vector_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.department, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.degree, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER courses_search_vector_trigger
        BEFORE INSERT OR UPDATE ON courses
        FOR EACH ROW EXECUTE FUNCTION courses_search_vector_update();
    """)

    # ── course_details ────────────────────────────────────────────────────────
    op.create_table(
        "course_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "course_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("description", sa.Text()),
        sa.Column("entry_requirements", sa.Text()),
        sa.Column("modules", sa.Text()),
        sa.Column("career_prospects", sa.Text()),
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS courses_search_vector_trigger ON courses")
    op.execute("DROP FUNCTION IF EXISTS courses_search_vector_update()")
    op.drop_table("course_details")
    op.drop_index("ix_courses_fts", table_name="courses")
    op.drop_table("courses")
    op.drop_table("universities")
