"""
RECOVERX AI — Database Setup
Supports SQLite (local dev) and PostgreSQL (production) via the same SQLAlchemy models.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Engine — use NullPool for SQLite (no connection pooling needed)
connect_args = {}
engine_kwargs: dict = {}

if settings.is_sqlite:
    connect_args = {"check_same_thread": False}
    # Use StaticPool for SQLite so in-memory tests work
    from sqlalchemy.pool import StaticPool
    engine_kwargs["poolclass"] = StaticPool

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug and False,  # Set True to log SQL
    connect_args=connect_args,
    **engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


async def init_db() -> None:
    """Create all tables on startup."""
    # Import models so they are registered with Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        if settings.is_sqlite:
            # Enable WAL mode and foreign keys for SQLite
            await conn.execute(__import__("sqlalchemy").text("PRAGMA journal_mode=WAL"))
            await conn.execute(__import__("sqlalchemy").text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    logger.info(f"Database initialized: {settings.database_url[:50]}")


async def get_db():
    """FastAPI dependency — yields an async DB session and commits on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Cleanly close and dispose of engine connection pool."""
    await engine.dispose()
