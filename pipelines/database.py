"""
pipelines/database.py
──────────────────────
Stage 4: Persist items to PostgreSQL using SQLAlchemy async.

Strategy:
  UPSERT on source_url (unique constraint).
  If a course was scraped before, only update it if data has changed.
  University rows are upserted by name — no duplicates.

Uses a synchronous psycopg2 connection (via run_sync) so Scrapy's
twisted-based pipeline system doesn't need an event loop.

Actually: Scrapy pipelines are synchronous by default. We use
asyncio.run() in a thread-safe way to do async DB ops.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import structlog
from scrapy import Spider
from sqlalchemy import select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from config.database import AsyncSessionLocal
from models.db import Course, CourseDetail, University

logger = structlog.get_logger(__name__)


from scrapy.utils.defer import deferred_from_coro

class DatabasePipeline:
    """
    Stage 4: Upsert course + university data to PostgreSQL.

    Batches writes in groups of BATCH_SIZE for efficiency.
    Flushes remaining items when spider closes.
    """

    BATCH_SIZE = 25

    def __init__(self) -> None:
        self._batch: list[dict] = []
        self._saved = 0
        self._errors = 0
        self._schema_checked = False

    async def process_item(self, item: dict, spider: Spider) -> dict:
        self._batch.append(item)
        if len(self._batch) >= self.BATCH_SIZE:
            await self._flush(spider)
        return item

    def close_spider(self, spider: Spider):
        if self._batch:
            d = deferred_from_coro(self._flush(spider))
            def _log(_):
                logger.info(
                    "db_pipeline_done",
                    spider=spider.name,
                    saved=self._saved,
                    errors=self._errors,
                )
            d.addCallback(_log)
            return d
        else:
            logger.info(
                "db_pipeline_done",
                spider=spider.name,
                saved=self._saved,
                errors=self._errors,
            )

    async def _flush(self, spider: Spider) -> None:
        batch = list(self._batch)
        self._batch.clear()
        try:
            await self._save_batch(batch)
            self._saved += len(batch)
        except Exception as exc:
            self._errors += len(batch)
            logger.error("db_batch_failed", error=str(exc), size=len(batch))

    async def _save_batch(self, items: list[dict]) -> None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                if not self._schema_checked:
                    await self._ensure_compat_schema(session)
                for item in items:
                    try:
                        await self._upsert_item(session, item)
                    except Exception as exc:
                        logger.error(
                            "db_item_failed",
                            url=item.get("metadata", {}).get("url"),
                            error=str(exc),
                        )

    async def _ensure_compat_schema(self, session) -> None:
        """
        Ensure older SQLite databases remain compatible with current code.
        Adds newly introduced columns if they are missing.
        """
        bind = session.get_bind()
        if not bind or bind.dialect.name != "sqlite":
            self._schema_checked = True
            return

        result = await session.execute(text("PRAGMA table_info(courses)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "raw_json" not in existing_columns:
            await session.execute(text("ALTER TABLE courses ADD COLUMN raw_json TEXT"))
            logger.info("db_schema_column_added", table="courses", column="raw_json")

        if "updated_at" not in existing_columns:
            await session.execute(text("ALTER TABLE courses ADD COLUMN updated_at DATETIME"))
            logger.info("db_schema_column_added", table="courses", column="updated_at")

        self._schema_checked = True

    async def _upsert_item(self, session, item: dict) -> None:
        uni_data = item.get("university", {})
        course_data = item.get("course", {})
        fees = item.get("fees", {})
        admission = item.get("admission", {})
        metadata = item.get("metadata", {})
        details_data = item.get("_details", {})   # injected by spider if available

        # ── 1. Upsert University ──────────────────────────────────────────────
        uni_stmt = (
            sqlite_insert(University)
            .values(
                id=uuid.uuid4(),
                name=uni_data.get("name", "Unknown"),
                location=uni_data.get("location"),
            )
            .on_conflict_do_update(
                index_elements=["name"],
                set_={"location": uni_data.get("location")},
            )
            .returning(University.id)
        )
        result = await session.execute(uni_stmt)
        university_id = result.scalar_one()

        # ── 2. Upsert Course ──────────────────────────────────────────────────
        scraped_at = datetime.now(timezone.utc)
        course_id = uuid.uuid4()

        study_modes = course_data.get("study_mode", ["full-time"])
        study_mode_str = ",".join(study_modes) if isinstance(study_modes, list) else study_modes

        course_stmt = (
            sqlite_insert(Course)
            .values(
                id=course_id,
                university_id=university_id,
                name=course_data.get("name", ""),
                degree=course_data.get("degree"),
                level=course_data.get("level"),
                department=course_data.get("department"),
                ucas_code=admission.get("ucas_code"),
                study_mode=study_mode_str,
                duration_years=course_data.get("duration_years"),
                start_month=course_data.get("start_month"),
                fee_uk_yearly=fees.get("uk", {}).get("yearly"),
                fee_uk_sandwich=fees.get("uk", {}).get("sandwich_year"),
                fee_intl_yearly=fees.get("international", {}).get("yearly"),
                fee_intl_sandwich=fees.get("international", {}).get("sandwich_year"),
                deadline_main=admission.get("application_deadline", {}).get("main"),
                deadline_late=admission.get("application_deadline", {}).get("late"),
                ielts_score=admission.get("english_requirement", {}).get("ielts"),
                source_url=metadata.get("url", ""),
                scraped_at=scraped_at,
                raw_json=json.dumps(item),
            )
            .on_conflict_do_update(
                index_elements=["source_url"],
                set_={
                    "name": course_data.get("name", ""),
                    "degree": course_data.get("degree"),
                    "level": course_data.get("level"),
                    "department": course_data.get("department"),
                    "ucas_code": admission.get("ucas_code"),
                    "study_mode": study_mode_str,
                    "duration_years": course_data.get("duration_years"),
                    "start_month": course_data.get("start_month"),
                    "fee_uk_yearly": fees.get("uk", {}).get("yearly"),
                    "fee_intl_yearly": fees.get("international", {}).get("yearly"),
                    "fee_uk_sandwich": fees.get("uk", {}).get("sandwich_year"),
                    "fee_intl_sandwich": fees.get("international", {}).get("sandwich_year"),
                    "deadline_main": admission.get("application_deadline", {}).get("main"),
                    "deadline_late": admission.get("application_deadline", {}).get("late"),
                    "ielts_score": admission.get("english_requirement", {}).get("ielts"),
                    "scraped_at": scraped_at,
                    "updated_at": scraped_at,
                    "raw_json": json.dumps(item),
                },
            )
            .returning(Course.id)
        )
        result = await session.execute(course_stmt)
        saved_course_id = result.scalar_one()

        # ── 3. Upsert CourseDetail (long text) ────────────────────────────────
        description = item.get("_raw_description") or admission.get("entry_requirements")
        entry_req = admission.get("entry_requirements")

        if description or entry_req:
            detail_stmt = (
                sqlite_insert(CourseDetail)
                .values(
                    id=uuid.uuid4(),
                    course_id=saved_course_id,
                    description=description,
                    entry_requirements=entry_req,
                )
                .on_conflict_do_update(
                    index_elements=["course_id"],
                    set_={
                        "description": description,
                        "entry_requirements": entry_req,
                    },
                )
            )
            await session.execute(detail_stmt)

        logger.debug(
            "course_upserted",
            name=course_data.get("name"),
            url=metadata.get("url"),
        )
