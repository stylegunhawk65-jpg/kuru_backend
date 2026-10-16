"""Pytest fixtures and test environment configuration."""

import os
from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Enforce testing environment variables prior to importing application settings
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.core.config import get_settings
from app.db.base import Base
import app.models  # Register all models on Base.metadata
from app.db.session import get_db
from app.main import create_app

# Clear cached settings so testing environment takes effect
get_settings.cache_clear()


@pytest.fixture
def test_settings():
    """Provide the active testing settings."""
    return get_settings()


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide an isolated in-memory SQLite async engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session rolled back after every test."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def app(test_engine: AsyncEngine):
    """Instantiate a FastAPI test app with database dependency overridden."""
    test_app = create_app()

    session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client for testing endpoints."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
