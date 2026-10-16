"""Job sources package exposing adapters, normalized schemas, and aggregation manager."""

from app.services.job_sources.adzuna import AdzunaAdapter
from app.services.job_sources.arbeitnow import ArbeitnowAdapter
from app.services.job_sources.base import BaseJobAdapter, NormalizedJob
from app.services.job_sources.curated_india import CuratedIndiaAdapter
from app.services.job_sources.partner import NaukriPartnerAdapter, UnstopPartnerAdapter
from app.services.job_sources.aggregator import JobSourceManager, job_source_manager

__all__ = [
    "NormalizedJob",
    "BaseJobAdapter",
    "CuratedIndiaAdapter",
    "ArbeitnowAdapter",
    "AdzunaAdapter",
    "UnstopPartnerAdapter",
    "NaukriPartnerAdapter",
    "JobSourceManager",
    "job_source_manager",
]
