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

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from scrapy import Spider
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from config.database import AsyncSessionLocal
from models.db import Course, CourseDetail, University

logger = structlog.get_logger(__name__)


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

    def process_item(self, item: dict, spider: Spider) -> dict:
        self._batch.append(item)
        if len(self._batch) >= self.BATCH_SIZE:
            self._flush(spider)
        return item

    def close_spider(self, spider: Spider) -> None:
        if self._batch:
            self._flush(spider)
        logger.info(
            "db_pipeline_done",
            spider=spider.name,
            saved=self._saved,
            errors=self._errors,
        )

    def _flush(self, spider: Spider) -> None:
        batch = list(self._batch)
        self._batch.clear()
        try:
            asyncio.run(self._save_batch(batch))
            self._saved += len(batch)
        except RuntimeError:
            # Already inside an event loop — use current loop
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._save_batch(batch))
            self._saved += len(batch)
        except Exception as exc:
            self._errors += len(batch)
            logger.error("db_batch_failed", error=str(exc), size=len(batch))

    async def _save_batch(self, items: list[dict]) -> None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for item in items:
                    try:
                        await self._upsert_item(session, item)
                    except Exception as exc:
                        logger.error(
                            "db_item_failed",
                            url=item.get("metadata", {}).get("url"),
                            error=str(exc),
                        )

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
