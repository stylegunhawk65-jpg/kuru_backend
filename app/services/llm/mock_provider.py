"""High-fidelity mock LLM provider for rapid development and testing without GPU/model downloads."""

import asyncio
import json
import time
from typing import TypeVar
from pydantic import BaseModel

from app.services.llm.base import BaseLLMProvider, LLMInferenceError, LLMResponse

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(BaseLLMProvider):
    """Deterministic mock provider that simulates LLM generation and structured schemas."""

    name = "mock"

    def __init__(self, simulate_latency: float = 0.0, fail_next: bool = False):
        self.simulate_latency = simulate_latency
        self.fail_next = fail_next

    def is_ready(self) -> bool:
        """Mock provider is always initialized and ready."""
        return True

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Simulate fast textual completion."""
        if self.fail_next:
            self.fail_next = False
            raise LLMInferenceError("Simulated LLM generation failure", provider=self.name)

        if self.simulate_latency > 0:
            await asyncio.sleep(self.simulate_latency)

        start_time = time.perf_counter()
        simulated_text = (
            f"[Mock LLM Output for prompt: '{prompt[:60]}...']\n"
            f"Synthesizing actionable Career Twin recommendations grounded in verified evidence."
        )
        latency = round(time.perf_counter() - start_time + self.simulate_latency, 4)

        return LLMResponse(
            text=simulated_text,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(simulated_text.split()),
            latency_seconds=latency,
            model_name="mock-qwen2.5-3b",
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> T:
        """Return valid, realistic structured responses tailored to Career Twin schemas."""
        if self.fail_next:
            self.fail_next = False
            raise LLMInferenceError("Simulated structured generation failure", provider=self.name)

        if self.simulate_latency > 0:
            await asyncio.sleep(self.simulate_latency)

        schema_name = schema.__name__

        # Handle specific Career Twin schemas with domain-accurate mock payloads
        if schema_name == "ResumeTailorResponse":
            mock_data = {
                "target_role": "Backend Engineer",
                "tailored_summary": (
                    "Results-oriented backend software engineer with hands-on experience building "
                    "high-performance RESTful microservices in Python, FastAPI, and PostgreSQL. "
                    "Demonstrated ability to architect scalable data pipelines and containerized services."
                ),
                "bullet_points": [
                    {
                        "original": "Worked on backend APIs.",
                        "tailored": "Architected and deployed 12+ asynchronous REST APIs using FastAPI and PostgreSQL, reducing query latency by 35% through connection pooling and index optimization.",
                        "highlighted_skills": ["Python", "FastAPI", "PostgreSQL"],
                        "impact_metric": "35% reduction in latency across 12 endpoints",
                    },
                    {
                        "original": "Helped with containerization.",
                        "tailored": "Configured multi-stage Docker builds and automated CI/CD deployment workflows, cutting artifact size by 45% and standardizing developer environments.",
                        "highlighted_skills": ["Docker", "CI/CD"],
                        "impact_metric": "45% reduction in container image size",
                    },
                ],
                "alignment_explanation": "Resume bullets refocused to directly address job requirements in API latency, PostgreSQL indexing, and containerization.",
            }
            return schema.model_validate(mock_data)

        elif schema_name == "RoadmapGenerateResponse":
            mock_data = {
                "target_role": "Backend Developer",
                "total_estimated_weeks": 4,
                "weekly_hours_required": 12,
                "weekly_modules": [
                    {
                        "week_number": 1,
                        "focus_skill": "Docker",
                        "objective": "Containerize existing FastAPI applications with multi-stage Dockerfiles and docker-compose.",
                        "daily_milestones": [
                            "Day 1-2: Understand image layers, non-root security, and build context caching.",
                            "Day 3-4: Write production multi-stage Dockerfile for FastAPI + PostgreSQL.",
                            "Day 5-7: Build local multi-container test harness with docker-compose.",
                        ],
                        "practical_project": "Containerized CRUD backend with persistent volume mounts.",
                    },
                    {
                        "week_number": 2,
                        "focus_skill": "Redis Caching",
                        "objective": "Implement distributed caching and session rate-limiting in backend microservices.",
                        "daily_milestones": [
                            "Day 1-2: Redis data structures (Strings, Hashes, Sorted Sets).",
                            "Day 3-4: Cache-aside pattern and TTL invalidation strategies.",
                            "Day 5-7: Implement sliding-window rate limiter on authenticated endpoints.",
                        ],
                        "practical_project": "Sub-millisecond cache layer for high-read profile endpoints.",
                    },
                ],
                "learning_principles": [
                    "Project-based application over passive video viewing.",
                    "Active GitHub commit history demonstrating verified evidence.",
                ],
            }
            return schema.model_validate(mock_data)

        elif schema_name == "InterviewPrepResponse":
            mock_data = {
                "target_role": "Backend Engineer",
                "company_focus": "Tech Platform",
                "technical_questions": [
                    {
                        "question": "How does PostgreSQL MVCC handle concurrent read and write operations without table-level locking?",
                        "expected_answer_points": [
                            "Snapshot isolation based on transaction IDs (xmin, xmax).",
                            "Readers never block writers and writers never block readers.",
                            "Need for periodic VACUUM to reclaim dead row versions.",
                        ],
                        "difficulty": "Medium",
                        "category": "Database Architecture",
                    },
                    {
                        "question": "Explain the difference between threading, multiprocessing, and asyncio in Python for high-throughput I/O.",
                        "expected_answer_points": [
                            "Global Interpreter Lock (GIL) constraint on CPU threads.",
                            "asyncio cooperative single-threaded event loop for network I/O.",
                            "Multiprocessing for true CPU-bound parallelism across cores.",
                        ],
                        "difficulty": "Hard",
                        "category": "Concurrency & Python Internals",
                    },
                ],
                "coding_challenge_topics": [
                    "LRU Cache implementation with O(1) get and put.",
                    "Distributed rate limiter using Redis token bucket.",
                ],
                "behavioral_tips": [
                    "Ground engineering decisions in concrete trade-offs (latency vs consistency).",
                    "Cite code evidence from your analyzed repositories.",
                ],
            }
            return schema.model_validate(mock_data)

        elif schema_name == "ProjectRecommendationsResponse":
            mock_data = {
                "target_role": "Backend Engineer",
                "summary": (
                    "Targeted portfolio projects designed to master missing skills (Redis, Docker) "
                    "while demonstrating production engineering readiness to hiring managers."
                ),
                "recommended_projects": [
                    {
                        "title": "High-Throughput Distributed API Rate-Limiter & Caching Gateway",
                        "description": "Architect an asynchronous reverse proxy with token-bucket rate limiting and cache-aside layers using FastAPI and Redis.",
                        "target_skill_gaps": ["Redis", "Distributed Systems"],
                        "tech_stack": ["Python", "FastAPI", "Redis", "Docker"],
                        "architecture_overview": "FastAPI reverse proxy -> Redis cluster for sliding-window token bucket -> PostgreSQL persistent layer.",
                        "portfolio_deliverable": "GitHub repo with Docker Compose orchestration, Locust load benchmark report, and architecture RFC.",
                        "estimated_duration_weeks": 2,
                        "difficulty_level": "Intermediate",
                    },
                    {
                        "title": "Containerized Event-Driven Microservices Worker System",
                        "description": "Build an asynchronous job processing system with retry queues, dead-letter exchanges, and transactional outbox patterns.",
                        "target_skill_gaps": ["Docker", "Event-Driven Architecture", "Microservices"],
                        "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Docker Compose"],
                        "architecture_overview": "REST API producer -> Transactional outbox -> Background consumer workers -> Idempotent updates.",
                        "portfolio_deliverable": "Production repository with multi-stage Dockerfiles, GitHub Actions CI pipeline, and integration tests.",
                        "estimated_duration_weeks": 3,
                        "difficulty_level": "Advanced",
                    },
                ],
            }
            return schema.model_validate(mock_data)

        elif schema_name == "ChallengeGeneratedSchema":
            mock_data = {
                "title": "FastAPI: Request Header Token Validator",
                "description": "Implement function `validate_auth_header(header: str) -> bool` that verifies Bearer token structure.",
                "entry_function": "validate_auth_header",
                "starter_code": "def validate_auth_header(header: str) -> bool:\n    # Implement here\n    pass\n",
                "public_tests": [
                    {"name": "test_valid_bearer", "args": ["Bearer valid_token_123"], "expected": True},
                    {"name": "test_missing_bearer", "args": ["Basic user:pass"], "expected": False},
                ],
                "hidden_tests": [
                    {"name": "test_empty_header", "args": [""], "expected": False},
                    {"name": "test_malformed_space", "args": ["Bearer   "], "expected": False},
                ],
                "difficulty": "Intermediate",
                "rubric": {"Correctness": 50, "Edge Cases": 30, "Cleanliness": 20},
            }
            return schema.model_validate(mock_data)

        # Fallback to generating a minimal valid instance of any generic schema
        try:
            return schema.model_validate({})
        except Exception:
            return await super().generate_structured(prompt, schema, system_prompt, max_tokens, temperature)
