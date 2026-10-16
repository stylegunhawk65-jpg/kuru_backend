"""Authoritative registry of verified, genuine learning resources for technical skills.

Strict Principle: Never invent, hallucinate, or fabricate URLs.
All resources are validated against official documentation and accredited developer platforms.
"""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

# Whitelist of verified, authoritative developer documentation and education domains
ALLOWED_OFFICIAL_DOMAINS = {
    "docs.python.org",
    "fastapi.tiangolo.com",
    "docs.docker.com",
    "www.postgresql.org",
    "postgresql.org",
    "react.dev",
    "developer.mozilla.org",
    "git-scm.com",
    "redis.io",
    "kubernetes.io",
    "aws.amazon.com",
    "cloud.google.com",
    "learn.microsoft.com",
    "www.freecodecamp.org",
    "freecodecamp.org",
    "go.dev",
    "doc.rust-lang.org",
    "www.typescriptlang.org",
    "nodejs.org",
    "graphql.org",
    "pydantic.dev",
    "docs.sqlalchemy.org",
    "alembic.sqlalchemy.org",
}


@dataclass(frozen=True)
class GenuineResource:
    """An authentic, verified learning resource with genuine source URL."""

    skill_name: str
    title: str
    url: str
    provider: str
    resource_type: str  # "official_documentation", "hands_on_tutorial", "interactive_course"
    difficulty: str  # "Beginner", "Intermediate", "Advanced"
    estimated_hours: int
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "title": self.title,
            "url": self.url,
            "provider": self.provider,
            "resource_type": self.resource_type,
            "difficulty": self.difficulty,
            "estimated_hours": self.estimated_hours,
            "description": self.description,
        }


def is_url_genuine(url: str) -> bool:
    """Validate that a URL uses HTTPS and belongs to an approved official domain."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        hostname = (parsed.hostname or "").lower()
        return any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in ALLOWED_OFFICIAL_DOMAINS
        )
    except Exception:
        return False


# Curated, authentic registry of official resources
VERIFIED_RESOURCES_REGISTRY: list[GenuineResource] = [
    # Python
    GenuineResource(
        skill_name="Python",
        title="Official Python Tutorial",
        url="https://docs.python.org/3/tutorial/",
        provider="Python Software Foundation",
        resource_type="official_documentation",
        difficulty="Beginner",
        estimated_hours=10,
        description="Comprehensive guide covering Python core syntax, data structures, OOP, and standard library.",
    ),
    GenuineResource(
        skill_name="Python",
        title="Python Typing & Type Hints Documentation",
        url="https://docs.python.org/3/library/typing.html",
        provider="Python Software Foundation",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=4,
        description="Official reference for static type annotations, Generics, and TypeVar in modern Python 3.12+.",
    ),
    # FastAPI
    GenuineResource(
        skill_name="FastAPI",
        title="FastAPI Official Tutorial - User Guide",
        url="https://fastapi.tiangolo.com/tutorial/",
        provider="FastAPI Official",
        resource_type="official_documentation",
        difficulty="Beginner",
        estimated_hours=8,
        description="Step-by-step tutorial on building production REST APIs, dependency injection, and Pydantic validation.",
    ),
    GenuineResource(
        skill_name="FastAPI",
        title="FastAPI Advanced User Guide & Security",
        url="https://fastapi.tiangolo.com/advanced/",
        provider="FastAPI Official",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=6,
        description="In-depth guide covering OAuth2, JWT tokens, background tasks, and custom middleware.",
    ),
    # Docker
    GenuineResource(
        skill_name="Docker",
        title="Docker Official Getting Started Guide",
        url="https://docs.docker.com/get-started/",
        provider="Docker Official",
        resource_type="hands_on_tutorial",
        difficulty="Beginner",
        estimated_hours=6,
        description="Hands-on walkthrough to build images, manage containers, and write multi-stage Dockerfiles.",
    ),
    GenuineResource(
        skill_name="Docker",
        title="Docker Compose Multi-Container Orchestration",
        url="https://docs.docker.com/compose/",
        provider="Docker Official",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=5,
        description="Define and run multi-container applications with networks, persistent volumes, and healthchecks.",
    ),
    # PostgreSQL
    GenuineResource(
        skill_name="PostgreSQL",
        title="PostgreSQL Official Tutorial",
        url="https://www.postgresql.org/docs/current/tutorial.html",
        provider="PostgreSQL Global Development Group",
        resource_type="official_documentation",
        difficulty="Beginner",
        estimated_hours=8,
        description="Core relational concepts, transactions, window functions, and indexing strategies.",
    ),
    GenuineResource(
        skill_name="PostgreSQL",
        title="PostgreSQL Performance Optimization & Indexing",
        url="https://www.postgresql.org/docs/current/indexes.html",
        provider="PostgreSQL Global Development Group",
        resource_type="official_documentation",
        difficulty="Advanced",
        estimated_hours=6,
        description="B-tree, GIN, GiST indexes, EXPLAIN ANALYZE query planning, and partition management.",
    ),
    # SQL
    GenuineResource(
        skill_name="SQL",
        title="PostgreSQL SQL Language Reference",
        url="https://www.postgresql.org/docs/current/sql.html",
        provider="PostgreSQL Global Development Group",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=8,
        description="Standard ANSI SQL commands, JOINs, subqueries, CTEs, and schema migrations.",
    ),
    # Redis
    GenuineResource(
        skill_name="Redis",
        title="Redis Quick Start & Data Structures Guide",
        url="https://redis.io/docs/latest/develop/get-started/",
        provider="Redis Official",
        resource_type="official_documentation",
        difficulty="Beginner",
        estimated_hours=4,
        description="In-memory caching, Pub/Sub, key expiration policies, and distributed session storage.",
    ),
    # Git
    GenuineResource(
        skill_name="Git",
        title="Pro Git Book & Official Reference",
        url="https://git-scm.com/doc",
        provider="Git Official Project",
        resource_type="official_documentation",
        difficulty="Beginner",
        estimated_hours=6,
        description="Distributed version control, branching strategies, interactive rebasing, and merge conflict resolution.",
    ),
    # React
    GenuineResource(
        skill_name="React",
        title="React Official Documentation - Describing the UI & Hooks",
        url="https://react.dev/learn",
        provider="Meta Open Source",
        resource_type="interactive_course",
        difficulty="Beginner",
        estimated_hours=12,
        description="Modern functional components, useState, useEffect, context, and custom hooks.",
    ),
    # TypeScript
    GenuineResource(
        skill_name="TypeScript",
        title="TypeScript Handbook for JavaScript Developers",
        url="https://www.typescriptlang.org/docs/handbook/intro.html",
        provider="Microsoft Official",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=8,
        description="Interfaces, Union types, Generics, narrowing, and configuration with tsconfig.",
    ),
    # Node.js
    GenuineResource(
        skill_name="Node.js",
        title="Node.js Official Developer Guides",
        url="https://nodejs.org/en/learn/getting-started/introduction-to-nodejs",
        provider="OpenJS Foundation",
        resource_type="official_documentation",
        difficulty="Beginner",
        estimated_hours=6,
        description="Event loop architecture, asynchronous I/O, npm package ecosystem, and streams.",
    ),
    # Kubernetes
    GenuineResource(
        skill_name="Kubernetes",
        title="Kubernetes Basics & Interactive Tutorials",
        url="https://kubernetes.io/docs/tutorials/kubernetes-basics/",
        provider="Cloud Native Computing Foundation",
        resource_type="hands_on_tutorial",
        difficulty="Intermediate",
        estimated_hours=10,
        description="Pods, Deployments, Services, Ingress controllers, and cluster scaling.",
    ),
    # AWS / Cloud
    GenuineResource(
        skill_name="AWS",
        title="AWS Getting Started Resource Center",
        url="https://aws.amazon.com/getting-started/",
        provider="Amazon Web Services",
        resource_type="hands_on_tutorial",
        difficulty="Intermediate",
        estimated_hours=8,
        description="Deploying cloud workloads with EC2, S3, RDS, Lambda, and IAM security best practices.",
    ),
    # REST APIs
    GenuineResource(
        skill_name="REST APIs",
        title="MDN Web Docs: HTTP Overview & REST Architecture",
        url="https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview",
        provider="MDN Web Docs",
        resource_type="official_documentation",
        difficulty="Beginner",
        estimated_hours=5,
        description="HTTP status codes, headers, idempotency, caching, and RESTful resource modeling.",
    ),
    # GraphQL
    GenuineResource(
        skill_name="GraphQL",
        title="GraphQL Official Introduction & Schema Guide",
        url="https://graphql.org/learn/",
        provider="GraphQL Foundation",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=6,
        description="Queries, mutations, type schemas, resolvers, and subscriptions.",
    ),
    # SQLAlchemy
    GenuineResource(
        skill_name="SQLAlchemy",
        title="SQLAlchemy 2.0 Unified Tutorial",
        url="https://docs.sqlalchemy.org/en/20/tutorial/",
        provider="SQLAlchemy Official",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=7,
        description="Async ORM mapping, session management, select statements, and connection pooling.",
    ),
    # Alembic
    GenuineResource(
        skill_name="Alembic",
        title="Alembic Official Migration Tutorial",
        url="https://alembic.sqlalchemy.org/en/latest/tutorial.html",
        provider="SQLAlchemy Official",
        resource_type="official_documentation",
        difficulty="Intermediate",
        estimated_hours=4,
        description="Schema revisions, autogenerate, async environment configuration, and downgrade scripts.",
    ),
]


class ResourceRegistryService:
    """Service providing lookup and verification for authentic learning resources."""

    @staticmethod
    def get_resources_for_skill(skill_name: str, limit: int = 3) -> list[GenuineResource]:
        """Lookup verified resources for a given skill with case-insensitive normalization."""
        norm_query = skill_name.lower().strip()
        matches = [
            res
            for res in VERIFIED_RESOURCES_REGISTRY
            if res.skill_name.lower() == norm_query
            or norm_query in res.skill_name.lower()
            or res.skill_name.lower() in norm_query
        ]

        if not matches:
            # Fallback to general software engineering foundational resources (MDN/FreeCodeCamp)
            matches = [
                GenuineResource(
                    skill_name=skill_name,
                    title=f"MDN Developer Guide for Web & Computing",
                    url="https://developer.mozilla.org/en-US/docs/Learn",
                    provider="MDN Web Docs",
                    resource_type="hands_on_tutorial",
                    difficulty="Beginner",
                    estimated_hours=8,
                    description=f"Foundational documentation and structured curriculum applicable to {skill_name}.",
                ),
                GenuineResource(
                    skill_name=skill_name,
                    title="FreeCodeCamp Technical Curriculum",
                    url="https://www.freecodecamp.org/learn",
                    provider="freeCodeCamp Official",
                    resource_type="interactive_course",
                    difficulty="Beginner",
                    estimated_hours=10,
                    description=f"Interactive exercises and building projects supporting {skill_name}.",
                ),
            ]

        # Ensure all emitted URLs are strictly verified
        verified = [res for res in matches if is_url_genuine(res.url)]
        return verified[:limit]

    @classmethod
    def get_resources_for_skills(
        cls,
        skills: list[str],
        limit_per_skill: int = 2,
    ) -> dict[str, list[dict[str, Any]]]:
        """Lookup genuine resources for multiple skills, returning JSON-serializable payloads."""
        results: dict[str, list[dict[str, Any]]] = {}
        for s in skills:
            res_list = cls.get_resources_for_skill(s, limit=limit_per_skill)
            results[s] = [r.to_dict() for r in res_list]
        return results


resource_registry = ResourceRegistryService()
get_curated_learning_resources = ResourceRegistryService.get_resources_for_skill
