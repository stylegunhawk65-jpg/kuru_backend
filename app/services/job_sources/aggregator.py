"""Orchestrator and aggregation manager for job sources, deduplication, and database synchronization."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobPosting, JobSource
from app.services.job_sources.adzuna import AdzunaAdapter
from app.services.job_sources.arbeitnow import ArbeitnowAdapter
from app.services.job_sources.base import BaseJobAdapter, NormalizedJob
from app.services.job_sources.curated_india import CuratedIndiaAdapter
from app.services.job_sources.partner import NaukriPartnerAdapter, UnstopPartnerAdapter

logger = logging.getLogger(__name__)


class JobSourceManager:
    """Manages adapter registration, execution, deduplication, and database persistence."""

    def __init__(self) -> None:
        self.adapters: dict[str, BaseJobAdapter] = {
            "curated_india": CuratedIndiaAdapter(),
            "arbeitnow": ArbeitnowAdapter(),
            "adzuna": AdzunaAdapter(),
            "unstop": UnstopPartnerAdapter(),
            "naukri": NaukriPartnerAdapter(),
        }

    def register_adapter(self, adapter: BaseJobAdapter) -> None:
        """Register or override a job source adapter."""
        self.adapters[adapter.source_name] = adapter

    def get_adapter(self, source_name: str) -> BaseJobAdapter | None:
        """Retrieve an adapter by name."""
        return self.adapters.get(source_name)

    async def ensure_job_sources_registered(self, db: AsyncSession) -> None:
        """Ensure all known adapters have a corresponding row in the job_sources table."""
        for name in self.adapters.keys():
            stmt = select(JobSource).where(JobSource.source_name == name)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                new_source = JobSource(
                    id=str(uuid.uuid4()),
                    source_name=name,
                    is_enabled=True,
                    last_sync_status="idle",
                    jobs_synced_count=0,
                )
                db.add(new_source)
        await db.commit()

    async def fetch_with_retry(
        self,
        adapter: BaseJobAdapter,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> list[NormalizedJob]:
        """Execute adapter fetch with retries on transient errors."""
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                return await adapter.fetch_jobs()
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Attempt %d/%d for adapter '%s' failed: %s",
                    attempt,
                    max_retries,
                    adapter.source_name,
                    exc,
                )
                if attempt < max_retries:
                    await asyncio.sleep(backoff_seconds * (2 ** (attempt - 1)))
        if last_exception:
            raise last_exception
        return []

    async def sync_source(self, db: AsyncSession, source_name: str) -> dict[str, Any]:
        """Synchronize a single source, upserting jobs and tracking status."""
        adapter = self.get_adapter(source_name)
        if not adapter:
            raise ValueError(f"Unknown job source: '{source_name}'")

        # Retrieve source DB record
        stmt = select(JobSource).where(JobSource.source_name == source_name)
        res = await db.execute(stmt)
        source_rec = res.scalar_one_or_none()
        if not source_rec:
            source_rec = JobSource(
                id=str(uuid.uuid4()),
                source_name=source_name,
                is_enabled=True,
                last_sync_status="in_progress",
                jobs_synced_count=0,
            )
            db.add(source_rec)
        else:
            source_rec.last_sync_status = "in_progress"
        await db.commit()

        synced_count = 0
        new_count = 0
        updated_count = 0

        try:
            raw_jobs = await self.fetch_with_retry(adapter)
            now = datetime.now(timezone.utc)

            for job in raw_jobs:
                dedup_hash = job.compute_dedup_hash()

                # Check if posting exists
                job_stmt = select(JobPosting).where(JobPosting.dedup_hash == dedup_hash)
                job_res = await db.execute(job_stmt)
                existing_posting = job_res.scalar_one_or_none()

                if existing_posting:
                    # Freshness update: mark active and bump last_seen_at
                    existing_posting.last_seen_at = now
                    existing_posting.is_active = True
                    if job.url:
                        existing_posting.url = job.url
                    if job.required_skills:
                        # Combine or update skills if richer
                        existing_posting.required_skills = list(
                            set(existing_posting.required_skills + job.required_skills)
                        )
                    updated_count += 1
                else:
                    new_posting = JobPosting(
                        id=str(uuid.uuid4()),
                        source=job.source,
                        source_id=job.source_id,
                        dedup_hash=dedup_hash,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        is_remote=job.is_remote,
                        job_type=job.job_type,
                        description=job.description,
                        url=job.url,
                        required_skills=job.required_skills,
                        salary_currency=job.salary_currency,
                        salary_min=job.salary_min,
                        salary_max=job.salary_max,
                        posted_at=job.posted_at or now,
                        last_seen_at=now,
                        is_active=True,
                    )
                    db.add(new_posting)
                    new_count += 1
                synced_count += 1

            source_rec.last_sync_at = now
            source_rec.last_sync_status = "success"
            source_rec.jobs_synced_count = synced_count
            source_rec.error_message = None
            await db.commit()

            return {
                "source": source_name,
                "status": "success",
                "total_synced": synced_count,
                "new_postings": new_count,
                "updated_postings": updated_count,
            }

        except Exception as exc:
            await db.rollback()
            logger.error("Sync failed for source '%s': %s", source_name, exc, exc_info=True)
            source_rec.last_sync_status = "failed"
            source_rec.error_message = str(exc)
            await db.commit()
            return {
                "source": source_name,
                "status": "failed",
                "error": str(exc),
                "total_synced": 0,
            }

    async def sync_all(self, db: AsyncSession) -> dict[str, Any]:
        """Synchronize all enabled job sources."""
        await self.ensure_job_sources_registered(db)
        results = {}
        for name, adapter in self.adapters.items():
            # Check if source is enabled in DB
            stmt = select(JobSource).where(JobSource.source_name == name)
            res = await db.execute(stmt)
            source_rec = res.scalar_one_or_none()
            if source_rec and not source_rec.is_enabled:
                logger.info("Source '%s' is disabled, skipping.", name)
                continue

            results[name] = await self.sync_source(db, name)
        return results

    async def get_source_statuses(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Retrieve the health and configuration status of all providers."""
        await self.ensure_job_sources_registered(db)
        stmt = select(JobSource)
        res = await db.execute(stmt)
        sources = res.scalars().all()

        status_list: list[dict[str, Any]] = []
        for src in sources:
            adapter = self.get_adapter(src.source_name)
            is_configured = adapter.is_configured() if adapter else False
            status_list.append(
                {
                    "id": src.id,
                    "source_name": src.source_name,
                    "is_enabled": src.is_enabled,
                    "is_configured": is_configured,
                    "last_sync_at": src.last_sync_at,
                    "last_sync_status": src.last_sync_status,
                    "jobs_synced_count": src.jobs_synced_count,
                    "error_message": src.error_message,
                }
            )
        return status_list


job_source_manager = JobSourceManager()
