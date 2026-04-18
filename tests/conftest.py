"""
tests/conftest.py
──────────────────
Shared pytest fixtures.

Provides:
  - `client`     — async httpx client wired to FastAPI app with test DB
  - `db_session` — bare async SQLAlchemy session for assertion queries
  - `sample_university` / `sample_course` — pre-seeded ORM rows
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.main import app
from config.database import get_db
from models.db import Base, Course, University

# ─── In-memory test database ─────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _override_get_db():
    """Replaces the real PostgreSQL get_db with an in-memory SQLite session."""
    async with _TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Apply dependency override globally for all tests
app.dependency_overrides[get_db] = _override_get_db


# ─── Session-scoped DB setup ────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    """Create all tables once per test session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


# ─── Function-scoped client ──────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        yield c


# ─── Function-scoped DB session ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    async with _TestSession() as session:
        yield session


# ─── Seed fixtures ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def sample_university(db_session) -> University:
    uni = University(
        id=uuid.uuid4(),
        name="Test University",
        location="London, England",
        website="https://test.ac.uk",
    )
    db_session.add(uni)
    await db_session.commit()
    await db_session.refresh(uni)
    return uni


@pytest_asyncio.fixture
async def sample_course(db_session, sample_university) -> Course:
    course = Course(
        id=uuid.uuid4(),
        university_id=sample_university.id,
        name="BSc Computer Science",
        degree="BSc",
        level="undergraduate",
        department="Computer Science",
        ucas_code="G400",
        study_mode="full-time",
        duration_years=3.0,
        start_month="September",
        fee_uk_yearly=9250,
        fee_intl_yearly=35000,
        ielts_score=6.5,
        source_url="https://test.ac.uk/courses/bsc-cs",
        scraped_at=datetime.now(timezone.utc),
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    return course
