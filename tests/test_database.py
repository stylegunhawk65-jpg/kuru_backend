"""Tests for database connectivity and ORM base mixins."""

import pytest
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.session import check_db_connectivity


class SampleModel(Base, TimestampMixin):
    """Temporary ORM model to test Base and TimestampMixin without affecting schema."""

    __tablename__ = "test_sample_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


@pytest.mark.asyncio
async def test_db_connectivity_success(db_session: AsyncSession):
    """Test connectivity verification with an active session."""
    health = await check_db_connectivity(db_session=db_session)
    assert health["status"] == "connected"
    assert health["latency_ms"] >= 0
    assert "operational" in health["message"]


@pytest.mark.asyncio
async def test_db_connectivity_failure():
    """Test connectivity helper returns disconnected status gracefully on error."""
    class BrokenSession:
        async def execute(self, *args, **kwargs):
            raise ConnectionRefusedError("Simulated connection timeout")

    health = await check_db_connectivity(db_session=BrokenSession())  # type: ignore
    assert health["status"] == "disconnected"
    assert "unreachable" in health["message"]


@pytest.mark.asyncio
async def test_base_model_and_timestamp_mixin(db_session: AsyncSession, test_engine):
    """Test table creation, ORM insertion, and automatic UTC timestamps."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SampleModel.__table__.create, checkfirst=True)

    item = SampleModel(name="Cloud Architect")
    db_session.add(item)
    await db_session.flush()

    stmt = select(SampleModel).where(SampleModel.name == "Cloud Architect")
    result = await db_session.execute(stmt)
    retrieved = result.scalar_one()

    assert retrieved.id is not None
    assert retrieved.name == "Cloud Architect"
    assert retrieved.created_at is not None
    assert retrieved.updated_at is not None
