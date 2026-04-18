"""
config/database.py
──────────────────
Async SQLAlchemy engine and session factory.
All database interaction uses asyncpg so nothing blocks the event loop.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "sqlite+aiosqlite:///./test.db",
    pool_pre_ping=True,
    echo=False,
)


# ─── Session factory ─────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Declarative base (imported by all ORM models) ───────────────────────────
class Base(DeclarativeBase):
    pass


# ─── FastAPI dependency ───────────────────────────────────────────────────────
# IMPORTANT: FastAPI's Depends() requires an *async generator* (yield-based),
# NOT an asynccontextmanager. Using @asynccontextmanager here breaks injection.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession; commit on success, rollback on exception."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
