"""Arbeitnow free public job board adapter."""

from datetime import datetime, timezone
import logging
from typing import Any
import httpx

from app.services.job_sources.base import BaseJobAdapter, NormalizedJob

logger = logging.getLogger(__name__)


class ArbeitnowAdapter(BaseJobAdapter):
    """Adapter for the Arbeitnow open tech job board API."""

    source_name = "arbeitnow"
    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def is_configured(self) -> bool:
        """Arbeitnow is a free open API requiring no credentials."""
        return True

    async def fetch_jobs(
        self,
        query: str | None = None,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[NormalizedJob]:
        """Fetch listings from Arbeitnow public endpoint."""
        params: dict[str, Any] = {"page": page}
        normalized_jobs: list[NormalizedJob] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                if response.status_code != 200:
                    logger.warning(
                        "Arbeitnow API returned non-200 status: %d", response.status_code
                    )
                    return []

                payload = response.json()
                raw_jobs = payload.get("data", [])

                for item in raw_jobs:
                    # Filter by query if supplied
                    title = item.get("title", "")
                    company = item.get("company_name", "")
                    description = item.get("description", "")
                    tags = item.get("tags", [])
                    job_loc = item.get("location", "Remote")
                    is_remote = bool(item.get("remote", False))

                    if query:
                        q_low = query.lower()
                        match = (
                            q_low in title.lower()
                            or q_low in company.lower()
                            or any(q_low in t.lower() for t in tags)
                        )
                        if not match:
                            continue

                    if location:
                        loc_low = location.lower()
                        if loc_low not in job_loc.lower() and not (
                            loc_low == "remote" and is_remote
                        ):
                            continue

                    # Determine job type
                    raw_types = [t.lower() for t in item.get("job_types", [])]
                    job_type = "full_time"
                    if any("intern" in t for t in raw_types):
                        job_type = "internship"
                    elif any("part" in t for t in raw_types):
                        job_type = "part_time"
                    elif any("contract" in t for t in raw_types):
                        job_type = "contract"

                    # Convert created_at unix timestamp if present
                    created_at_ts = item.get("created_at")
                    posted_at = None
                    if isinstance(created_at_ts, (int, float)):
                        posted_at = datetime.fromtimestamp(created_at_ts, tz=timezone.utc)

                    source_id = str(item.get("slug") or item.get("id") or f"{company}-{title}")
                    url = item.get("url") or f"https://www.arbeitnow.com/view/{source_id}"

                    normalized_jobs.append(
                        NormalizedJob(
                            source=self.source_name,
                            source_id=source_id,
                            title=title,
                            company=company,
                            location=job_loc,
                            is_remote=is_remote,
                            job_type=job_type,
                            description=description,
                            url=url,
                            required_skills=tags,
                            salary_currency=None,
                            salary_min=None,
                            salary_max=None,
                            posted_at=posted_at,
                        )
                    )

                    if len(normalized_jobs) >= limit:
                        break

        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            logger.error("Failed to fetch jobs from Arbeitnow: %s", exc)
            return []

        return normalized_jobs
