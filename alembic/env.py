"""
alembic/env.py
───────────────
Alembic migration environment.

Uses a SYNCHRONOUS psycopg2 URL (not asyncpg) because Alembic's migration
runner is synchronous. The async engine is used only by the app at runtime.
"""

from __future__ import annotations

import os
import re
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

load_dotenv()

# Alembic Config object — gives access to alembic.ini values
config = context.config

# Override sqlalchemy.url from environment variable
# Convert asyncpg URL → psycopg2 URL for alembic's sync runner
raw_url = os.environ.get("DATABASE_URL", "")
sync_url = raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
config.set_main_option("sqlalchemy.url", sync_url)

# Set up loggers from alembic.ini
if config.config_file_name:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
from models.db import Base   # noqa: E402  (must be after sys.path setup)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to DB and applies)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,         # detect column type changes
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
