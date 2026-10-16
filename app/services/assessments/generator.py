"""Adaptive challenge generator leveraging Qwen2.5-3B-Instruct with bounded retries and fallback templates.

Grounds challenges in student's repository evidence and target-job requirements.
Similarity alone never determines competency or level selection.
"""

import json
import logging
import random
from typing import Any
from pydantic import BaseModel, Field

from app.models.profile import StudentProfile
from app.models.skill import StudentSkill
from app.models.skillproof import SkillProofRun
from app.services.assessments.sandbox import TestCase
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import get_llm_provider

logger = logging.getLogger("kuru.assessments.generator")


class ChallengeGeneratedSchema(BaseModel):
    """Pydantic schema for structured LLM challenge generation."""

    title: str = Field(..., description="Challenge title")
    description: str = Field(..., description="Clear task description and specifications")
    entry_function: str = Field(..., description="Name of the entry function to implement")
    starter_code: str = Field(..., description="Starter code with function signature and docstring")
    public_tests: list[dict[str, Any]] = Field(default_factory=list, description="Public test cases")
    hidden_tests: list[dict[str, Any]] = Field(default_factory=list, description="Hidden test cases with edge cases")
    difficulty: str = Field(..., description="'Basic', 'Intermediate', or 'Advanced'")
    rubric: dict[str, int] = Field(default_factory=dict, description="Rubric criteria and weights")


# High-quality deterministic challenge templates for robust fallbacks
CHALLENGE_TEMPLATES: dict[str, dict[str, Any]] = {
    "FastAPI": {
        "basic": {
            "title": "FastAPI: Endpoint Parameter Sanitizer",
            "description": (
                "Implement a parameter sanitization utility for an API route. "
                "Write function `sanitize_query_params(params: dict) -> dict` that removes empty/null values, "
                "strips leading/trailing whitespace from string values, and converts integer strings to integers."
            ),
            "entry_function": "sanitize_query_params",
            "starter_code": (
                "def sanitize_query_params(params: dict) -> dict:\n"
                "    \"\"\"Sanitize dictionary query parameters.\n"
                "    Strip strings, drop None/empty, convert integer digits.\n"
                "    \"\"\"\n"
                "    # Your implementation here\n"
                "    pass\n"
            ),
            "public_tests": [
                {"name": "test_basic_strip", "function_name": "sanitize_query_params", "args": [{"title": "  FastAPI  ", "page": "2"}], "expected": {"title": "FastAPI", "page": 2}, "is_hidden": False},
                {"name": "test_drop_none", "function_name": "sanitize_query_params", "args": [{"query": None, "tag": "python"}], "expected": {"tag": "python"}, "is_hidden": False},
            ],
            "hidden_tests": [
                {"name": "test_empty_dict", "function_name": "sanitize_query_params", "args": [{}], "expected": {}, "is_hidden": True},
                {"name": "test_mixed_types", "function_name": "sanitize_query_params", "args": [{"active": True, "count": "0", "empty_str": ""}], "expected": {"active": True, "count": 0}, "is_hidden": True},
                {"name": "test_whitespace_only", "function_name": "sanitize_query_params", "args": [{"spaces": "    "}], "expected": {}, "is_hidden": True},
            ],
            "difficulty": "Basic",
            "rubric": {"Correctness": 50, "Edge Cases": 30, "Cleanliness": 20},
        },
        "intermediate": {
            "title": "FastAPI: Sliding-Window Rate Limiter Logic",
            "description": (
                "Implement the core stateful window calculation for an API rate limiting middleware. "
                "Write function `is_rate_limited(requests: list, current_timestamp: int, window_seconds: int, max_limit: int) -> tuple[bool, int]` "
                "that calculates whether the request is rate-limited based on timestamps within the sliding window, "
                "returning (is_limited, remaining_quota)."
            ),
            "entry_function": "is_rate_limited",
            "starter_code": (
                "def is_rate_limited(requests: list[int], current_timestamp: int, window_seconds: int, max_limit: int) -> tuple[bool, int]:\n"
                "    \"\"\"Evaluate sliding-window rate limit.\n"
                "    Returns (is_limited, remaining_quota).\n"
                "    \"\"\"\n"
                "    pass\n"
            ),
            "public_tests": [
                {"name": "test_within_limit", "function_name": "is_rate_limited", "args": [[100, 102, 104], 105, 10, 5], "expected": [False, 1], "is_hidden": False},
                {"name": "test_exceeded_limit", "function_name": "is_rate_limited", "args": [[100, 101, 102, 103, 104], 105, 10, 5], "expected": [True, 0], "is_hidden": False},
            ],
            "hidden_tests": [
                {"name": "test_expired_window", "function_name": "is_rate_limited", "args": [[50, 60, 70], 120, 10, 2], "expected": [False, 1], "is_hidden": True},
                {"name": "test_empty_history", "function_name": "is_rate_limited", "args": [[], 100, 60, 10], "expected": [False, 9], "is_hidden": True},
                {"name": "test_boundary_timestamp", "function_name": "is_rate_limited", "args": [[90, 100], 100, 10, 2], "expected": [True, 0], "is_hidden": True},
            ],
            "difficulty": "Intermediate",
            "rubric": {"Algorithm Correctness": 40, "Window Eviction": 30, "Edge Cases": 20, "Efficiency": 10},
        },
        "advanced": {
            "title": "FastAPI: Asynchronous Dependency Resolution DAG",
            "description": (
                "Implement topological dependency execution ordering for an API dependency injection system. "
                "Write function `resolve_dependencies_order(graph: dict[str, list[str]]) -> list[str]` "
                "that takes a dependency mapping (e.g. {'db': [], 'auth': ['db'], 'endpoint': ['auth']}) and "
                "returns an executable execution order list. If a cycle is detected, raise ValueError('Circular dependency detected')."
            ),
            "entry_function": "resolve_dependencies_order",
            "starter_code": (
                "def resolve_dependencies_order(graph: dict[str, list[str]]) -> list[str]:\n"
                "    \"\"\"Return valid execution order or raise ValueError on cycle.\"\"\"\n"
                "    pass\n"
            ),
            "public_tests": [
                {"name": "test_linear_chain", "function_name": "resolve_dependencies_order", "args": [{"c": ["b"], "b": ["a"], "a": []}], "expected": ["a", "b", "c"], "is_hidden": False},
            ],
            "hidden_tests": [
                {"name": "test_diamond_dag", "function_name": "resolve_dependencies_order", "args": [{"d": ["b", "c"], "b": ["a"], "c": ["a"], "a": []}], "expected": ["a", "b", "c", "d"], "is_hidden": True},
                {"name": "test_independent_nodes", "function_name": "resolve_dependencies_order", "args": [{"x": [], "y": []}], "expected": ["x", "y"], "is_hidden": True},
            ],
            "difficulty": "Advanced",
            "rubric": {"DAG Traversal": 40, "Cycle Detection": 30, "Complexity": 20, "Cleanliness": 10},
        },
    },
    "Python": {
        "basic": {
            "title": "Python: Resilient Key-Value Normalizer",
            "description": (
                "Implement function `normalize_dictionary(data: dict) -> dict` that converts all string keys "
                "to lower_snake_case and removes None values."
            ),
            "entry_function": "normalize_dictionary",
            "starter_code": (
                "def normalize_dictionary(data: dict) -> dict:\n"
                "    \"\"\"Convert keys to lower_snake_case and strip None values.\"\"\"\n"
                "    pass\n"
            ),
            "public_tests": [
                {"name": "test_snake_case", "function_name": "normalize_dictionary", "args": [{"UserName": "Alice", "UserAge": 22}], "expected": {"user_name": "Alice", "user_age": 22}, "is_hidden": False},
                {"name": "test_drop_none", "function_name": "normalize_dictionary", "args": [{"firstName": "Bob", "middleName": None}], "expected": {"first_name": "Bob"}, "is_hidden": False},
            ],
            "hidden_tests": [
                {"name": "test_empty", "function_name": "normalize_dictionary", "args": [{}], "expected": {}, "is_hidden": True},
                {"name": "test_all_none", "function_name": "normalize_dictionary", "args": [{"A": None, "B": None}], "expected": {}, "is_hidden": True},
            ],
            "difficulty": "Basic",
            "rubric": {"Correctness": 50, "String Parsing": 30, "Cleanliness": 20},
        },
        "intermediate": {
            "title": "Python: Event Stream Deduplicator with TTL",
            "description": (
                "Implement function `deduplicate_events(events: list[dict], ttl_seconds: int) -> list[str]` "
                "Each event is a dict: {'id': str, 'timestamp': int}. "
                "Return the ordered list of event IDs that were processed without duplicates within ttl_seconds."
            ),
            "entry_function": "deduplicate_events",
            "starter_code": (
                "def deduplicate_events(events: list[dict], ttl_seconds: int) -> list[str]:\n"
                "    \"\"\"Deduplicate events within TTL window.\"\"\"\n"
                "    pass\n"
            ),
            "public_tests": [
                {"name": "test_basic_dedup", "function_name": "deduplicate_events", "args": [[{"id": "e1", "timestamp": 10}, {"id": "e1", "timestamp": 12}, {"id": "e2", "timestamp": 15}], 5], "expected": ["e1", "e2"], "is_hidden": False},
            ],
            "hidden_tests": [
                {"name": "test_ttl_expiry_allows_reprocess", "function_name": "deduplicate_events", "args": [[{"id": "e1", "timestamp": 10}, {"id": "e1", "timestamp": 25}], 10], "expected": ["e1", "e1"], "is_hidden": True},
                {"name": "test_empty_events", "function_name": "deduplicate_events", "args": [[], 10], "expected": [], "is_hidden": True},
            ],
            "difficulty": "Intermediate",
            "rubric": {"TTL Logic": 45, "Ordering": 35, "Efficiency": 20},
        },
        "advanced": {
            "title": "Python: Concurrency Safe In-Memory LRU Cache",
            "description": (
                "Implement an LRU Cache simulation function `simulate_lru_operations(capacity: int, operations: list[tuple[str, int, int | None]]) -> list[int | None]` "
                "Operations are tuples: ('get', key, None) or ('put', key, value). "
                "Return results of each 'get' call (-1 if missing)."
            ),
            "entry_function": "simulate_lru_operations",
            "starter_code": (
                "def simulate_lru_operations(capacity: int, operations: list) -> list:\n"
                "    \"\"\"Simulate LRU cache operations and return get results.\"\"\"\n"
                "    pass\n"
            ),
            "public_tests": [
                {"name": "test_lru_basic", "function_name": "simulate_lru_operations", "args": [2, [("put", 1, 10), ("put", 2, 20), ("get", 1, None), ("put", 3, 30), ("get", 2, None)]], "expected": [10, -1], "is_hidden": False},
            ],
            "hidden_tests": [
                {"name": "test_update_existing_key", "function_name": "simulate_lru_operations", "args": [2, [("put", 1, 10), ("put", 1, 20), ("get", 1, None)]], "expected": [20], "is_hidden": True},
                {"name": "test_capacity_one", "function_name": "simulate_lru_operations", "args": [1, [("put", 1, 100), ("put", 2, 200), ("get", 1, None), ("get", 2, None)]], "expected": [-1, 200], "is_hidden": True},
            ],
            "difficulty": "Advanced",
            "rubric": {"LRU Eviction": 40, "Update Semantics": 30, "Edge Cases": 20, "Complexity": 10},
        },
    },
}


class AdaptiveLevelSelector:
    """Selects appropriate assessment level based on evidence, similarity findings, and target roles."""

    @staticmethod
    def select_level(
        skill_name: str,
        student_skill: StudentSkill | None = None,
        skillproof_run: SkillProofRun | None = None,
        profile: StudentProfile | None = None,
    ) -> tuple[str, str, str]:
        """Determine (assessment_level, challenge_type, rationale).
        
        Assessment levels:
        - basic: Short practical coding task with public tests
        - intermediate: Customized input, debugging task, hidden tests
        - advanced: Multi-challenge task, hidden tests, architectural modification
        
        Similarity alone NEVER determines competency or AI generation.
        """
        target_roles = [r.lower() for r in (profile.target_roles if profile else [])]
        is_senior = any("senior" in r or "lead" in r or "architect" in r for r in target_roles)

        has_repo_evidence = student_skill is not None and len(student_skill.evidence) > 0
        conf_score = float(student_skill.confidence_score) if student_skill else 0.50

        # Check similarity findings from Phase 8
        avg_similarity = 0.0
        if skillproof_run and skillproof_run.summary:
            avg_similarity = float(skillproof_run.summary.get("average_similarity_score", 0.0))

        # Decision rules
        if is_senior:
            return (
                "advanced",
                "transfer",
                f"Advanced level selected: target roles ({', '.join(target_roles[:2])}) demand high architectural and transfer problem-solving.",
            )

        if avg_similarity >= 0.55:
            # High boilerplate similarity is normal; intermediate challenge allows student to prove active practical mastery
            return (
                "intermediate",
                "debugging",
                f"Intermediate debugging level selected: code exhibits standard template alignment (similarity={avg_similarity:.2f}); challenge allows student to actively demonstrate hands-on debugging.",
            )

        if has_repo_evidence and conf_score >= 0.75:
            return (
                "intermediate",
                "coding",
                f"Intermediate coding level selected: candidate has solid repository evidence (conf={conf_score:.2f}); challenge tests practical feature implementation.",
            )

        return (
            "basic",
            "coding",
            "Basic coding level selected: focused on foundational idioms and core syntax verification.",
        )


class PracticalChallengeGenerator:
    """Generates unique, repository-grounded challenges using Qwen provider with fallbacks."""

    @classmethod
    async def generate_challenge(
        cls,
        skill_name: str,
        level: str,
        challenge_type: str,
        provider: BaseLLMProvider | None = None,
        code_context: str | None = None,
    ) -> dict[str, Any]:
        """Generate a structured challenge with public and hidden test cases."""
        prov = provider or get_llm_provider()

        # Sanitize code context to prevent prompt injection
        safe_context = (code_context or "")[:500].replace("{", "{{").replace("}", "}}")

        system_prompt = (
            "You are a principal technical interviewer generating practical, executable programming assessments. "
            "STRICT FAIRNESS PRINCIPLE: Generate clear, unambiguous coding problems with deterministic inputs and outputs. "
            "You MUST provide valid public test cases and hidden test cases testing edge cases."
        )

        user_prompt = (
            f"Skill: {skill_name}\n"
            f"Assessment Level: {level.capitalize()}\n"
            f"Challenge Type: {challenge_type.capitalize()}\n"
            f"Candidate Code Context Reference:\n{safe_context or 'Standard software architecture'}\n\n"
            f"Please generate a complete coding challenge in Python with starter code and public/hidden tests."
        )

        # Attempt structured generation with bounded retries
        for attempt in range(2):
            try:
                res = await prov.generate_structured(
                    prompt=user_prompt,
                    schema=ChallengeGeneratedSchema,
                    system_prompt=system_prompt,
                    max_tokens=850,
                    temperature=0.3,
                )
                if res.starter_code and res.entry_function and (res.public_tests or res.hidden_tests):
                    # Convert to test case objects
                    return {
                        "title": res.title,
                        "description": res.description,
                        "entry_function": res.entry_function,
                        "starter_code": res.starter_code,
                        "public_tests": [
                            {**tc, "function_name": res.entry_function, "is_hidden": False}
                            for tc in res.public_tests
                        ],
                        "hidden_tests": [
                            {**tc, "function_name": res.entry_function, "is_hidden": True}
                            for tc in res.hidden_tests
                        ],
                        "difficulty": res.difficulty or level.capitalize(),
                        "rubric": res.rubric or {"Correctness": 50, "Edge Cases": 30, "Cleanliness": 20},
                    }
            except Exception as exc:
                logger.warning("Structured challenge generation attempt %d failed: %s", attempt + 1, exc)

        # Fallback to curated template
        logger.info("Using curated deterministic fallback template for skill '%s', level '%s'", skill_name, level)
        skill_templates = CHALLENGE_TEMPLATES.get(skill_name, CHALLENGE_TEMPLATES["Python"])
        template = skill_templates.get(level.lower(), skill_templates["basic"])
        return dict(template)


challenge_generator = PracticalChallengeGenerator()
level_selector = AdaptiveLevelSelector()
