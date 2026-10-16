"""Enterprise and partner API adapters for platforms with strict API access terms (Unstop, Naukri).

NOTE: In accordance with our compliance and terms-of-service rules, we NEVER
scrape, circumvent bot protections, or fabricate listings. Direct API access
is exclusively activated when legitimate partner/enterprise API keys are supplied.
"""

from datetime import datetime, timezone
import logging
from typing import Any
import httpx

from app.core.config import settings
from app.services.job_sources.base import BaseJobAdapter, NormalizedJob

logger = logging.getLogger(__name__)


class UnstopPartnerAdapter(BaseJobAdapter):
    """Partner adapter for Unstop student internships and job opportunities."""

    source_name = "unstop"
    BASE_URL = "https://api.unstop.com/v1/partner/opportunities"

    def is_configured(self) -> bool:
        """Check if official Unstop Partner API key is configured."""
        return bool(settings.UNSTOP_API_KEY)

    async def fetch_jobs(
        self,
        query: str | None = None,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[NormalizedJob]:
        """Fetch listings from official Unstop Partner API when permitted."""
        if not self.is_configured():
            logger.info(
                "Unstop Partner API credentials not configured. In compliance with Unstop terms, "
                "automated scraping is disabled. Set UNSTOP_API_KEY to activate partner sync."
            )
            return []

        headers = {
            "Authorization": f"Bearer {settings.UNSTOP_API_KEY}",
            "Accept": "application/json",
        }
        params: dict[str, Any] = {"page": page, "per_page": limit}
        if query:
            params["query"] = query
        if location:
            params["location"] = location

        normalized_jobs: list[NormalizedJob] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, headers=headers, params=params)
                if response.status_code != 200:
                    logger.warning(
                        "Unstop Partner API returned status %d", response.status_code
                    )
                    return []

                payload = response.json()
                items = payload.get("data", [])
                for item in items:
                    source_id = str(item.get("id"))
                    title = item.get("title", "")
                    company = item.get("organisation_name", "Unstop Partner")
                    loc = item.get("location", "India")
                    desc = item.get("details", "")
                    url = item.get("seo_url") or f"https://unstop.com/o/{source_id}"
                    skills = item.get("required_skills", [])
                    is_remote = bool(item.get("is_virtual", False))
                    job_type = "internship" if item.get("type") == "internship" else "full_time"

                    normalized_jobs.append(
                        NormalizedJob(
                            source=self.source_name,
                            source_id=source_id,
                            title=title,
                            company=company,
                            location=loc,
                            is_remote=is_remote,
                            job_type=job_type,
                            description=desc,
                            url=url,
                            required_skills=skills,
                            salary_currency="INR",
                            posted_at=datetime.now(timezone.utc),
                        )
                    )
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            logger.error("Failed to query Unstop Partner API: %s", exc)
            return []

        return normalized_jobs


class NaukriPartnerAdapter(BaseJobAdapter):
    """Partner adapter for Naukri / Info Edge enterprise recruitment API."""

    source_name = "naukri"
    BASE_URL = "https://api.naukri.com/v1/enterprise/jobs"

    def is_configured(self) -> bool:
        """Check if official Naukri Enterprise API key is configured."""
        return bool(settings.NAUKRI_API_KEY)

    async def fetch_jobs(
        self,
        query: str | None = None,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[NormalizedJob]:
        """Fetch listings from official Naukri Enterprise API when permitted."""
        if not self.is_configured():
            logger.info(
                "Naukri Enterprise API credentials not configured. In compliance with Info Edge / Naukri "
                "terms of service, unauthenticated scraping is disabled. Set NAUKRI_API_KEY to activate."
            )
            return []

        headers = {
            "Authorization": f"Bearer {settings.NAUKRI_API_KEY}",
            "Accept": "application/json",
        }
        params: dict[str, Any] = {"page": page, "size": limit}
        if query:
            params["keyword"] = query
        if location:
            params["city"] = location

        normalized_jobs: list[NormalizedJob] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, headers=headers, params=params)
                if response.status_code != 200:
                    logger.warning(
                        "Naukri Enterprise API returned status %d", response.status_code
                    )
                    return []

                payload = response.json()
                items = payload.get("jobs", [])
                for item in items:
                    source_id = str(item.get("job_id"))
                    title = item.get("title", "")
                    company = item.get("company_name", "Naukri Partner")
                    loc = item.get("location", "India")
                    desc = item.get("job_description", "")
                    url = item.get("apply_url") or f"https://www.naukri.com/job-listings-{source_id}"
                    skills = item.get("key_skills", [])
                    is_remote = "remote" in loc.lower() or "remote" in title.lower()

                    normalized_jobs.append(
                        NormalizedJob(
                            source=self.source_name,
                            source_id=source_id,
                            title=title,
                            company=company,
                            location=loc,
                            is_remote=is_remote,
                            job_type="full_time",
                            description=desc,
                            url=url,
                            required_skills=skills,
                            salary_currency="INR",
                            posted_at=datetime.now(timezone.utc),
                        )
                    )
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            logger.error("Failed to query Naukri Enterprise API: %s", exc)
            return []

        return normalized_jobs
