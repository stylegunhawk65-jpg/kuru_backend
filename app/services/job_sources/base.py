"""Base abstractions and normalized data transfer objects for job sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import re


def normalize_string(val: str) -> str:
    """Normalize string by removing excessive whitespace and lowercase."""
    return re.sub(r"\s+", " ", val or "").strip().lower()


@dataclass
class NormalizedJob:
    """Standardized representation of a job posting across any provider."""

    source: str
    source_id: str
    title: str
    company: str
    location: str
    is_remote: bool = False
    job_type: str = "full_time"  # full_time, internship, part_time, contract
    description: str = ""
    url: str = ""
    required_skills: list[str] = field(default_factory=list)
    salary_currency: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    posted_at: datetime | None = None

    def compute_dedup_hash(self) -> str:
        """Compute deterministic SHA-256 hash for deduplication.

        Based on normalized company, title, and location so duplicate listings
        across providers or reposts are mapped to the same canonical entity.
        """
        norm_company = normalize_string(self.company)
        norm_title = normalize_string(self.title)
        norm_loc = normalize_string(self.location)

        seed = f"{norm_company}|{norm_title}|{norm_loc}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()


class BaseJobAdapter(ABC):
    """Abstract base class for job and internship provider adapters."""

    source_name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether the necessary API keys or permissions are present."""
        pass

    @abstractmethod
    async def fetch_jobs(
        self,
        query: str | None = None,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[NormalizedJob]:
        """Fetch and normalize job postings from the external source."""
        pass
