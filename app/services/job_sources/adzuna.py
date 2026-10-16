"""Adzuna API adapter for India jobs and internships."""

from datetime import datetime
import logging
from typing import Any
import httpx

from app.core.config import settings
from app.services.job_sources.base import BaseJobAdapter, NormalizedJob

logger = logging.getLogger(__name__)


class AdzunaAdapter(BaseJobAdapter):
    """Adapter for official Adzuna job search API targeting the Indian market."""

    source_name = "adzuna"
    BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search/{page}"

    def is_configured(self) -> bool:
        """Check if Adzuna app credentials are configured."""
        return bool(settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY)

    async def fetch_jobs(
        self,
        query: str | None = None,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[NormalizedJob]:
        """Fetch jobs from Adzuna India endpoint."""
        if not self.is_configured():
            logger.info("Adzuna credentials not configured; skipping remote sync.")
            return []

        url = self.BASE_URL.format(page=page)
        params: dict[str, Any] = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": min(limit, 50),
            "content-type": "application/json",
        }
        if query:
            params["what"] = query
        if location:
            params["where"] = location

        normalized_jobs: list[NormalizedJob] = []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    logger.warning(
                        "Adzuna API returned status %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return []

                data = response.json()
                results = data.get("results", [])

                for item in results:
                    source_id = str(item.get("id"))
                    title = item.get("title", "")
                    company = (item.get("company") or {}).get("display_name", "Unknown")
                    loc_info = (item.get("location") or {}).get("display_name", "India")
                    desc = item.get("description", "")
                    redirect_url = item.get("redirect_url", "")
                    salary_min = item.get("salary_min")
                    salary_max = item.get("salary_max")
                    contract_time = item.get("contract_time") or ""

                    is_remote = "remote" in title.lower() or "remote" in desc.lower()
                    job_type = "internship" if "intern" in title.lower() else "full_time"
                    if "part_time" in contract_time or "part" in title.lower():
                        job_type = "part_time"

                    # Parse created timestamp
                    posted_at = None
                    created_str = item.get("created")
                    if created_str:
                        try:
                            posted_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    # Attempt to extract common tech skills from title and description
                    potential_skills = [
                        "Python", "Java", "Go", "Rust", "C++", "JavaScript", "TypeScript",
                        "React", "Node.js", "FastAPI", "Django", "SQL", "PostgreSQL",
                        "MongoDB", "Docker", "Kubernetes", "AWS", "Git"
                    ]
                    found_skills = [
                        s for s in potential_skills
                        if s.lower() in title.lower() or s.lower() in desc.lower()
                    ]

                    normalized_jobs.append(
                        NormalizedJob(
                            source=self.source_name,
                            source_id=source_id,
                            title=title,
                            company=company,
                            location=loc_info,
                            is_remote=is_remote,
                            job_type=job_type,
                            description=desc,
                            url=redirect_url,
                            required_skills=found_skills,
                            salary_currency="INR",
                            salary_min=float(salary_min) if salary_min is not None else None,
                            salary_max=float(salary_max) if salary_max is not None else None,
                            posted_at=posted_at,
                        )
                    )

        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            logger.error("Failed to query Adzuna India API: %s", exc)
            return []

        return normalized_jobs
