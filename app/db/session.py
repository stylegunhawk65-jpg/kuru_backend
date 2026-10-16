"""Database session management and connectivity verification."""

import logging
import time
from collections.abc import AsyncGenerator
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger("kuru.db")


def create_engine_and_session(
    database_url: str | None = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create async engine and session factory with connection pooling."""
    url = database_url or settings.DATABASE_URL

    is_sqlite = url.startswith("sqlite")
    engine_kwargs: dict[str, Any] = {
        "echo": False,
        "future": True,
    }

    # Add pool settings for non-sqlite databases (like PostgreSQL)
    if not is_sqlite:
        engine_kwargs.update({
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_pre_ping": True,
        })

    engine = create_async_engine(url, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, session_factory


# Module-level engine and session factory
engine, async_session_factory = create_engine_and_session()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connectivity(
    db_session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Test database connectivity with a SELECT 1 query."""
    start_time = time.perf_counter()
    try:
        if db_session is not None:
            result = await db_session.execute(text("SELECT 1"))
            result.scalar_one()
        else:
            async with async_session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar_one()

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "connected",
            "latency_ms": latency_ms,
            "message": "Database is operational",
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning("Database connectivity check failed: %s", str(exc))
        return {
            "status": "disconnected",
            "latency_ms": latency_ms,
            "message": "Database is unreachable or not yet configured",
        }


async def close_db_engine() -> None:
    """Dispose of the database engine connection pool."""
    if engine:
        logger.info("Disposing database connection pool")
        await engine.dispose()
