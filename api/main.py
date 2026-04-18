"""
api/main.py
────────────
FastAPI application entry point.

Features:
  - Async lifespan (creates DB tables on startup)
  - CORS configured for dev; tighten origins in production
  - Structured JSON error responses
  - /health and /ready endpoints for container orchestration
  - OpenAPI docs at /docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import courses, universities
from config.database import engine
from models.db import Base

logger = structlog.get_logger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup (Alembic manages migrations in prod)."""
    logger.info("api_startup", msg="Creating database tables if not exist")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("api_ready")
    yield
    logger.info("api_shutdown")
    await engine.dispose()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="UK University Course API",
    description=(
        "Search and filter 50+ UK university courses. "
        "Data collected by the UK Uni Scraper pipeline."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Tighten allow_origins in production (replace "*" with your frontend domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ─── Global error handler ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ─── Health endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"], summary="Liveness probe")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready", tags=["ops"], summary="Readiness probe")
async def ready() -> dict:
    """Checks DB connectivity."""
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready", "db": "connected"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "db": str(exc)},
        )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(courses.router, prefix="/courses", tags=["courses"])
app.include_router(universities.router, prefix="/universities", tags=["universities"])
