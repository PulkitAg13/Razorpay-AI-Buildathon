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
    """Create all tables on startup and apply SQLite column migrations if needed."""
    # Import models so they are registered with Base.metadata
    import app.models  # noqa: F401
    import sqlalchemy as sa

    async with engine.begin() as conn:
        if settings.is_sqlite:
            # Enable WAL mode and foreign keys for SQLite
            await conn.execute(sa.text("PRAGMA journal_mode=WAL"))
            await conn.execute(sa.text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

        if settings.is_sqlite:
            await _migrate_sqlite_columns(conn)

    logger.info(f"Database initialized: {settings.database_url[:50]}")


async def _migrate_sqlite_columns(conn) -> None:
    """Safely ensure any recently added columns exist in existing SQLite tables."""
    import sqlalchemy as sa
    tables_cols = {
        "audit_logs": [
            ("decision_source", "VARCHAR(32) DEFAULT 'DETERMINISTIC'"),
            ("step_index", "INTEGER DEFAULT 0"),
            ("llm_provider", "VARCHAR(64)"),
            ("llm_model", "VARCHAR(64)"),
            ("llm_used", "INTEGER DEFAULT 0"),
            ("used_fallback", "INTEGER DEFAULT 0"),
            ("input_json", "TEXT"),
            ("output_json", "TEXT"),
            ("had_error", "INTEGER DEFAULT 0"),
            ("error_message", "TEXT"),
            ("duration_ms", "FLOAT DEFAULT 0.0"),
        ],
        "recovery_cases": [
            ("status", "VARCHAR(32) DEFAULT 'CREATED'"),
            ("current_step", "VARCHAR(64)"),
            ("root_cause", "VARCHAR(64)"),
            ("selected_strategy", "VARCHAR(64)"),
            ("policy_approved", "BOOLEAN DEFAULT 0"),
            ("outcome_status", "VARCHAR(32)"),
            ("recovered_amount", "FLOAT DEFAULT 0.0"),
            ("recovery_cost", "FLOAT DEFAULT 0.0"),
            ("revenue_at_risk", "FLOAT DEFAULT 0.0"),
            ("expected_recovery_value", "FLOAT DEFAULT 0.0"),
            ("error_count", "INTEGER DEFAULT 0"),
            ("errors_json", "TEXT"),
            ("human_escalation_required", "BOOLEAN DEFAULT 0"),
            ("is_simulation", "BOOLEAN DEFAULT 1"),
            ("sentinel_output_json", "TEXT"),
            ("diagnosis_output_json", "TEXT"),
            ("customer_profile_json", "TEXT"),
            ("opportunity_score_json", "TEXT"),
            ("candidate_strategies_json", "TEXT"),
            ("twin_predictions_json", "TEXT"),
            ("guardian_decision_json", "TEXT"),
            ("execution_result_json", "TEXT"),
            ("learning_update_json", "TEXT"),
        ],
        "human_reviews": [
            ("policy_checks_json", "TEXT"),
            ("amount_at_risk", "FLOAT DEFAULT 0.0"),
            ("ai_confidence", "FLOAT DEFAULT 0.5"),
            ("candidate_strategies_json", "TEXT"),
            ("twin_predictions_json", "TEXT"),
            ("ai_recommendation_json", "TEXT"),
            ("reasoning_summary", "TEXT"),
            ("reviewer_notes", "TEXT"),
            ("modified_strategy_json", "TEXT"),
        ],
    }

    for table, cols in tables_cols.items():
        try:
            res = await conn.execute(sa.text(f"PRAGMA table_info({table})"))
            existing = {row[1] for row in res.fetchall()}
            if existing:
                for col_name, col_def in cols:
                    if col_name not in existing:
                        await conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
        except Exception:
            pass



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
