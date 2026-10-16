"""Curated legitimate Indian tech jobs and internships with verifiable career links."""

from datetime import datetime, timezone
import logging
from typing import Any

from app.services.job_sources.base import BaseJobAdapter, NormalizedJob

logger = logging.getLogger(__name__)

CURATED_INDIAN_LISTINGS: list[dict[str, Any]] = [
    {
        "source_id": "curated_zerodha_001",
        "title": "Junior Backend Engineer (Go / Python)",
        "company": "Zerodha",
        "location": "Bengaluru, Karnataka, India",
        "is_remote": False,
        "job_type": "full_time",
        "description": "Work on ultra-low latency trading systems, order execution engines, and market data feeds. We value simplicity, clean modular code, and direct understanding of operating systems and networking fundamentals.",
        "url": "https://zerodha.com/careers",
        "required_skills": ["Go", "Python", "PostgreSQL", "Redis", "Linux", "Distributed Systems"],
        "salary_currency": "INR",
        "salary_min": 1200000.0,
        "salary_max": 1800000.0,
        "posted_at": datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_razorpay_002",
        "title": "Software Engineering Intern - Payments Platform",
        "company": "Razorpay",
        "location": "Bengaluru, Karnataka, India",
        "is_remote": False,
        "job_type": "internship",
        "description": "Join India's leading fintech platform as a Software Engineering Intern. You will contribute to payment gateways, automated reconciliation, and developer API tooling.",
        "url": "https://razorpay.com/jobs/",
        "required_skills": ["Python", "FastAPI", "MySQL", "Docker", "REST APIs"],
        "salary_currency": "INR",
        "salary_min": 40000.0,  # Monthly stipend
        "salary_max": 60000.0,
        "posted_at": datetime(2026, 3, 5, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_swiggy_003",
        "title": "Associate Software Engineer - Logistics Engine",
        "company": "Swiggy",
        "location": "Bengaluru, Karnataka, India",
        "is_remote": False,
        "job_type": "full_time",
        "description": "Design and build dispatch algorithms, routing systems, and real-time tracking services serving millions of orders every day across 500+ Indian cities.",
        "url": "https://careers.swiggy.com/",
        "required_skills": ["Java", "Spring Boot", "Kafka", "PostgreSQL", "AWS"],
        "salary_currency": "INR",
        "salary_min": 1400000.0,
        "salary_max": 2000000.0,
        "posted_at": datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_cred_004",
        "title": "Backend Engineering Intern",
        "company": "CRED",
        "location": "Bengaluru, Karnataka, India",
        "is_remote": False,
        "job_type": "internship",
        "description": "Build high-throughput microservices for rewards, financial transactions, and user verification workflows with high security and low latency.",
        "url": "https://cred.club/careers",
        "required_skills": ["Java", "Kotlin", "Microservices", "PostgreSQL", "Redis"],
        "salary_currency": "INR",
        "salary_min": 50000.0,
        "salary_max": 75000.0,
        "posted_at": datetime(2026, 3, 12, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_postman_005",
        "title": "Software Engineer - Developer Productivity (Remote India)",
        "company": "Postman",
        "location": "Remote, India",
        "is_remote": True,
        "job_type": "full_time",
        "description": "Help millions of API developers build, test, and document their APIs. You will work on API specifications, CLI tooling, and collaborative developer workspaces.",
        "url": "https://www.postman.com/company/careers/",
        "required_skills": ["TypeScript", "Node.js", "React", "GraphQL", "Git"],
        "salary_currency": "INR",
        "salary_min": 1800000.0,
        "salary_max": 2400000.0,
        "posted_at": datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_hasura_006",
        "title": "Cloud Platform Intern",
        "company": "Hasura",
        "location": "Bengaluru / Remote, India",
        "is_remote": True,
        "job_type": "internship",
        "description": "Contribute to Hasura's GraphQL and instant API engine infrastructure on Kubernetes, observability pipelines, and developer documentation.",
        "url": "https://hasura.io/careers/",
        "required_skills": ["Go", "Haskell", "Kubernetes", "Docker", "GraphQL", "PostgreSQL"],
        "salary_currency": "INR",
        "salary_min": 45000.0,
        "salary_max": 65000.0,
        "posted_at": datetime(2026, 3, 18, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_juspay_007",
        "title": "Functional Programmer (Haskell / PureScript / Rust)",
        "company": "Juspay",
        "location": "Bengaluru, Karnataka, India",
        "is_remote": False,
        "job_type": "full_time",
        "description": "Pioneer functional programming in payments processing over 100 million transactions a day for UPI and major Indian apps.",
        "url": "https://juspay.in/careers",
        "required_skills": ["Haskell", "Rust", "Functional Programming", "Linux", "Data Structures"],
        "salary_currency": "INR",
        "salary_min": 1500000.0,
        "salary_max": 2200000.0,
        "posted_at": datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_flipkart_008",
        "title": "Associate Software Engineer - Supply Chain Tech",
        "company": "Flipkart",
        "location": "Bengaluru, Karnataka, India",
        "is_remote": False,
        "job_type": "full_time",
        "description": "Join Flipkart's Supply Chain technology group to optimize fulfillment centers, automated inventory tracking, and warehouse robotics interfaces.",
        "url": "https://www.flipkartcareers.com/",
        "required_skills": ["Java", "Python", "SQL", "Kafka", "Distributed Systems"],
        "salary_currency": "INR",
        "salary_min": 1600000.0,
        "salary_max": 2200000.0,
        "posted_at": datetime(2026, 3, 22, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_tcs_009",
        "title": "Graduate Trainee - Cloud & Modern Application Development",
        "company": "Tata Consultancy Services (TCS)",
        "location": "Hyderabad / Pune, India",
        "is_remote": False,
        "job_type": "full_time",
        "description": "Digital engineering initiatives across banking, retail, and healthcare. Opportunities to train and deploy modern cloud, microservices, and AI applications.",
        "url": "https://www.tcs.com/careers/india",
        "required_skills": ["Python", "Java", "SQL", "Git", "Problem Solving"],
        "salary_currency": "INR",
        "salary_min": 400000.0,
        "salary_max": 750000.0,
        "posted_at": datetime(2026, 3, 25, 0, 0, tzinfo=timezone.utc),
    },
    {
        "source_id": "curated_infosys_010",
        "title": "Specialist Programmer / Systems Engineer",
        "company": "Infosys",
        "location": "Pune / Bengaluru, India",
        "is_remote": False,
        "job_type": "full_time",
        "description": "Entry-level high-impact engineering role focused on competitive programming, algorithmic optimization, and enterprise full-stack software development.",
        "url": "https://www.infosys.com/careers/",
        "required_skills": ["C++", "Java", "Python", "Data Structures", "Algorithms"],
        "salary_currency": "INR",
        "salary_min": 600000.0,
        "salary_max": 950000.0,
        "posted_at": datetime(2026, 3, 28, 0, 0, tzinfo=timezone.utc),
    },
]


class CuratedIndiaAdapter(BaseJobAdapter):
    """Adapter providing verified Indian tech ecosystem jobs and internships."""

    source_name = "curated_india"

    def is_configured(self) -> bool:
        """Curated listings are bundled and always available."""
        return True

    async def fetch_jobs(
        self,
        query: str | None = None,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[NormalizedJob]:
        """Filter and return curated legitimate Indian listings."""
        results: list[NormalizedJob] = []

        q_lower = query.lower().strip() if query else None
        loc_lower = location.lower().strip() if location else None

        for item in CURATED_INDIAN_LISTINGS:
            # Query filter (title, company, description, skills)
            if q_lower:
                title_match = q_lower in item["title"].lower()
                company_match = q_lower in item["company"].lower()
                desc_match = q_lower in item["description"].lower()
                skill_match = any(q_lower in s.lower() for s in item["required_skills"])
                if not (title_match or company_match or desc_match or skill_match):
                    continue

            # Location filter
            if loc_lower:
                if loc_lower not in item["location"].lower() and not (
                    loc_lower == "remote" and item["is_remote"]
                ):
                    continue

            job = NormalizedJob(
                source=self.source_name,
                source_id=item["source_id"],
                title=item["title"],
                company=item["company"],
                location=item["location"],
                is_remote=item["is_remote"],
                job_type=item["job_type"],
                description=item["description"],
                url=item["url"],
                required_skills=item["required_skills"],
                salary_currency=item["salary_currency"],
                salary_min=item["salary_min"],
                salary_max=item["salary_max"],
                posted_at=item["posted_at"],
            )
            results.append(job)

        # Pagination
        start = (page - 1) * limit
        return results[start : start + limit]
