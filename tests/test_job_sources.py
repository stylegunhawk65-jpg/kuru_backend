"""Tests for Job Source Adapters, Normalization, Deduplication, and Sync Orchestration."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobPosting, JobSource
from app.services.job_sources.adzuna import AdzunaAdapter
from app.services.job_sources.arbeitnow import ArbeitnowAdapter
from app.services.job_sources.base import NormalizedJob, normalize_string
from app.services.job_sources.curated_india import CuratedIndiaAdapter
from app.services.job_sources.partner import NaukriPartnerAdapter, UnstopPartnerAdapter
from app.services.job_sources.aggregator import JobSourceManager


def test_normalize_string():
    """Test string whitespace normalization and lowercasing."""
    assert normalize_string("  Bengaluru,   Karnataka  ") == "bengaluru, karnataka"
    assert normalize_string("Software   Engineer\n") == "software engineer"
    assert normalize_string("") == ""


def test_normalized_job_dedup_hash():
    """Test deterministic deduplication hash generation."""
    job1 = NormalizedJob(
        source="curated_india",
        source_id="job1",
        title="Backend Engineer",
        company="Zerodha",
        location="Bengaluru",
    )
    job2 = NormalizedJob(
        source="adzuna",
        source_id="different_id_999",
        title="  backend   engineer  ",
        company="zerodha",
        location="BENGALURU",
    )
    job3 = NormalizedJob(
        source="arbeitnow",
        source_id="job3",
        title="Frontend Engineer",
        company="Zerodha",
        location="Bengaluru",
    )

    assert job1.compute_dedup_hash() == job2.compute_dedup_hash()
    assert job1.compute_dedup_hash() != job3.compute_dedup_hash()
    assert len(job1.compute_dedup_hash()) == 64  # SHA-256 length


@pytest.mark.asyncio
async def test_curated_india_adapter():
    """Test CuratedIndiaAdapter returns verified Indian tech postings."""
    adapter = CuratedIndiaAdapter()
    assert adapter.is_configured() is True

    # Fetch all
    jobs = await adapter.fetch_jobs(limit=50)
    assert len(jobs) >= 10
    for j in jobs:
        assert j.company in ["Zerodha", "Razorpay", "Swiggy", "CRED", "Postman", "Hasura", "Juspay", "Flipkart", "Tata Consultancy Services (TCS)", "Infosys"]
        assert j.url.startswith("http")
        assert len(j.required_skills) > 0

    # Query filter
    py_jobs = await adapter.fetch_jobs(query="Python")
    assert len(py_jobs) > 0
    assert all("python" in j.title.lower() or "python" in [s.lower() for s in j.required_skills] or "python" in j.description.lower() for j in py_jobs)

    # Location filter
    remote_jobs = await adapter.fetch_jobs(location="remote")
    assert len(remote_jobs) > 0
    assert all(j.is_remote for j in remote_jobs)


@pytest.mark.asyncio
async def test_arbeitnow_adapter_success():
    """Test ArbeitnowAdapter with mocked HTTP 200 payload."""
    adapter = ArbeitnowAdapter()
    assert adapter.is_configured() is True

    mock_payload = {
        "data": [
            {
                "slug": "senior-python-dev-123",
                "company_name": "Tech Corp",
                "title": "Senior Python Developer",
                "description": "Building backend APIs using FastAPI and PostgreSQL.",
                "remote": True,
                "url": "https://arbeitnow.com/jobs/senior-python-dev-123",
                "tags": ["Python", "FastAPI", "PostgreSQL"],
                "job_types": ["full_time"],
                "location": "Remote",
                "created_at": 1710000000,
            }
        ]
    }

    mock_response = httpx.Response(status_code=200, json=mock_payload, request=httpx.Request("GET", adapter.BASE_URL))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        jobs = await adapter.fetch_jobs()
        assert len(jobs) == 1
        job = jobs[0]
        assert job.source == "arbeitnow"
        assert job.company == "Tech Corp"
        assert job.title == "Senior Python Developer"
        assert job.is_remote is True
        assert "FastAPI" in job.required_skills


@pytest.mark.asyncio
async def test_arbeitnow_adapter_network_failure():
    """Test ArbeitnowAdapter returns empty list gracefully on network timeout/error."""
    adapter = ArbeitnowAdapter()

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectTimeout("Network timed out")):
        jobs = await adapter.fetch_jobs()
        assert jobs == []


@pytest.mark.asyncio
async def test_adzuna_adapter_unconfigured():
    """Test AdzunaAdapter reports unconfigured and returns empty list when keys absent."""
    adapter = AdzunaAdapter()

    with patch("app.core.config.settings.ADZUNA_APP_ID", None), patch(
        "app.core.config.settings.ADZUNA_APP_KEY", None
    ):
        assert adapter.is_configured() is False
        jobs = await adapter.fetch_jobs()
        assert jobs == []


@pytest.mark.asyncio
async def test_adzuna_adapter_configured():
    """Test AdzunaAdapter fetches and extracts tech skills when keys configured."""
    adapter = AdzunaAdapter()

    mock_payload = {
        "results": [
            {
                "id": "adzuna_987",
                "title": "Full Stack Software Engineer",
                "company": {"display_name": "Adzuna Partner"},
                "location": {"display_name": "Bengaluru, Karnataka"},
                "description": "Requires strong proficiency in Python, React, and Docker.",
                "redirect_url": "https://adzuna.com/redirect/987",
                "salary_min": 800000.0,
                "salary_max": 1200000.0,
                "contract_time": "full_time",
                "created": "2026-03-01T12:00:00Z",
            }
        ]
    }
    mock_response = httpx.Response(status_code=200, json=mock_payload, request=httpx.Request("GET", "https://api.adzuna.com"))

    with patch("app.core.config.settings.ADZUNA_APP_ID", "test_app_id"), patch(
        "app.core.config.settings.ADZUNA_APP_KEY", "test_app_key"
    ), patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        assert adapter.is_configured() is True
        jobs = await adapter.fetch_jobs()
        assert len(jobs) == 1
        job = jobs[0]
        assert job.source == "adzuna"
        assert job.company == "Adzuna Partner"
        assert "Python" in job.required_skills
        assert "React" in job.required_skills
        assert "Docker" in job.required_skills


@pytest.mark.asyncio
async def test_partner_adapters_compliance():
    """Test Unstop and Naukri partner adapters respect terms and remain disabled without enterprise keys."""
    unstop = UnstopPartnerAdapter()
    naukri = NaukriPartnerAdapter()

    with patch("app.core.config.settings.UNSTOP_API_KEY", None), patch(
        "app.core.config.settings.NAUKRI_API_KEY", None
    ):
        assert unstop.is_configured() is False
        assert naukri.is_configured() is False
        assert await unstop.fetch_jobs() == []
        assert await naukri.fetch_jobs() == []


@pytest.mark.asyncio
async def test_job_source_manager_deduplication(db_session: AsyncSession):
    """Test JobSourceManager upsert deduplication and last_seen freshness update."""
    manager = JobSourceManager()

    # Sync curated_india first time
    res1 = await manager.sync_source(db_session, "curated_india")
    assert res1["status"] == "success"
    assert res1["new_postings"] >= 10
    assert res1["updated_postings"] == 0

    # Count postings in DB
    count_stmt = select(JobPosting)
    total1 = len((await db_session.execute(count_stmt)).scalars().all())
    assert total1 >= 10

    # Sync again - duplicate listings should update freshness without creating new rows
    res2 = await manager.sync_source(db_session, "curated_india")
    assert res2["status"] == "success"
    assert res2["new_postings"] == 0
    assert res2["updated_postings"] == total1

    total2 = len((await db_session.execute(count_stmt)).scalars().all())
    assert total2 == total1


@pytest.mark.asyncio
async def test_job_source_manager_source_statuses(db_session: AsyncSession):
    """Test get_source_statuses initializes DB records and reports proper fields."""
    manager = JobSourceManager()
    statuses = await manager.get_source_statuses(db_session)

    source_names = [s["source_name"] for s in statuses]
    assert "curated_india" in source_names
    assert "arbeitnow" in source_names
    assert "adzuna" in source_names
    assert "unstop" in source_names
    assert "naukri" in source_names

    curated = next(s for s in statuses if s["source_name"] == "curated_india")
    assert curated["is_configured"] is True
    assert curated["is_enabled"] is True
