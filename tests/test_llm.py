"""Tests for Phase 6 LLM Provider Interface, Structured Generation, Tasks, and Endpoints."""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import CareerAssessment
from app.models.skill import StudentSkill
from app.schemas.intelligence import PrioritizedGapItem
from app.schemas.llm import (
    InterviewPrepRequest,
    InterviewPrepResponse,
    ResumeTailorRequest,
    ResumeTailorResponse,
    RoadmapGenerateRequest,
    RoadmapGenerateResponse,
)
from app.services.llm.base import (
    BaseLLMProvider,
    LLMInferenceError,
    LLMResponse,
    StructuredOutputError,
    extract_json_from_text,
)
from app.services.llm.career_tasks import CareerTaskService, career_task_service
from app.services.llm.factory import LLMProviderFactory, get_llm_provider
from app.services.llm.local_transformers import LocalTransformersProvider
from app.services.llm.mock_provider import MockLLMProvider


# Mock Firebase auth token helper
def mock_verify_token(token: str, *args, **kwargs):
    if token == "token_user_a":
        return {
            "uid": "usr_alpha_12345",
            "email": "student_alpha@example.com",
            "name": "Alpha Student",
        }
    elif token == "token_user_b":
        return {
            "uid": "usr_bravo_67890",
            "email": "student_bravo@example.com",
            "name": "Bravo Student",
        }
    raise ValueError("Unrecognized test token")


@pytest.fixture(autouse=True)
def patch_firebase_auth():
    """Automatically mock token verification for LLM tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}


class SimpleTestSchema(BaseModel):
    name: str
    score: int


def test_extract_json_from_text():
    """Test robust JSON substring extraction from markdown code fences or plain text."""
    # 1. Markdown code block
    md_text = "Here is the response:\n```json\n{\"name\": \"Alice\", \"score\": 95}\n```\nHope that helps!"
    assert extract_json_from_text(md_text) == '{"name": "Alice", "score": 95}'

    # 2. Raw unadorned JSON with outer prose
    raw_text = "Result: {\"name\": \"Bob\", \"score\": 88} (end of message)"
    assert extract_json_from_text(raw_text) == '{"name": "Bob", "score": 88}'

    # 3. JSON Array
    arr_text = "Items: [{\"id\": 1}, {\"id\": 2}]"
    assert extract_json_from_text(arr_text) == '[{"id": 1}, {"id": 2}]'


@pytest.mark.asyncio
async def test_mock_llm_provider_generation():
    """Test MockLLMProvider produces valid text and structured objects instantly."""
    provider = MockLLMProvider()
    assert provider.is_ready() is True

    # 1. Text generation
    resp = await provider.generate("Summarize my backend experience.")
    assert isinstance(resp, LLMResponse)
    assert len(resp.text) > 0
    assert resp.model_name == "mock-qwen2.5-3b"

    # 2. Structured generation for ResumeTailorResponse
    tailor_res = await provider.generate_structured("prompt", ResumeTailorResponse)
    assert isinstance(tailor_res, ResumeTailorResponse)
    assert len(tailor_res.bullet_points) >= 2
    assert tailor_res.bullet_points[0].impact_metric != ""

    # 3. Structured generation for RoadmapGenerateResponse
    roadmap_res = await provider.generate_structured("prompt", RoadmapGenerateResponse)
    assert isinstance(roadmap_res, RoadmapGenerateResponse)
    assert len(roadmap_res.weekly_modules) >= 2

    # 4. Structured generation for InterviewPrepResponse
    interview_res = await provider.generate_structured("prompt", InterviewPrepResponse)
    assert isinstance(interview_res, InterviewPrepResponse)
    assert len(interview_res.technical_questions) >= 2


@pytest.mark.asyncio
async def test_mock_llm_provider_failure_modes():
    """Test MockLLMProvider properly simulates error handling and exceptions."""
    provider = MockLLMProvider(fail_next=True)
    with pytest.raises(LLMInferenceError):
        await provider.generate("test prompt")

    provider = MockLLMProvider(fail_next=True)
    with pytest.raises(LLMInferenceError):
        await provider.generate_structured("test prompt", SimpleTestSchema)


def test_local_transformers_provider_lazy_loading_and_safety(monkeypatch):
    """Test LocalTransformersProvider initializes safely without downloading weights."""
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    provider = LocalTransformersProvider(
        model_id="Qwen/Qwen2.5-3B-Instruct",
        device="cuda",
        quantization="4bit",
    )
    # Model should NOT be loaded upon instantiation
    assert provider.is_ready() is False

    # Memory stats should report valid dict without error
    stats = provider.get_memory_stats()
    assert "vram_allocated_mb" in stats
    assert "cuda_available" in stats


def test_llm_provider_factory():
    """Test LLMProviderFactory instantiation and switching."""
    factory = LLMProviderFactory()

    mock_p = factory.get_provider("mock")
    assert isinstance(mock_p, MockLLMProvider)
    assert mock_p.name == "mock"

    local_p = factory.get_provider("local")
    assert isinstance(local_p, LocalTransformersProvider)
    assert local_p.name == "local"

    factory.reset()
    assert len(factory._providers) == 0


@pytest.mark.asyncio
async def test_career_task_service_resume_tailoring():
    """Test CareerTaskService resume tailoring with verified student skills."""
    provider = MockLLMProvider()
    skills = [
        StudentSkill(
            firebase_uid="usr_alpha_12345",
            skill_name="Python",
            category="Language",
            confidence_score=0.95,
        ),
        StudentSkill(
            firebase_uid="usr_alpha_12345",
            skill_name="FastAPI",
            category="Framework",
            confidence_score=0.90,
        ),
    ]

    req = ResumeTailorRequest(
        target_role="Backend Developer",
        bullet_points=["Built microservices."],
        job_description="Seeking FastAPI engineer.",
    )

    res = await career_task_service.tailor_resume_bullet_points(provider, skills, req)
    assert isinstance(res, ResumeTailorResponse)
    assert res.target_role == "Backend Engineer"
    assert len(res.bullet_points) > 0


@pytest.mark.asyncio
async def test_career_task_service_learning_roadmap():
    """Test CareerTaskService learning roadmap generation."""
    provider = MockLLMProvider()
    gaps = [
        PrioritizedGapItem(
            skill_name="Docker",
            priority_rank=1,
            priority_score=95.0,
            market_demand_pct=80.0,
            graph_proximity="1-Hop",
            reasons=["High demand"],
        )
    ]
    req = RoadmapGenerateRequest(
        target_role="Backend Engineer",
        focus_skills=["Docker"],
        weekly_hours_available=15,
    )

    res = await career_task_service.generate_learning_roadmap(provider, gaps, req)
    assert isinstance(res, RoadmapGenerateResponse)
    assert res.total_estimated_weeks >= 1
    assert len(res.weekly_modules) >= 1


@pytest.mark.asyncio
async def test_career_task_service_interview_prep():
    """Test CareerTaskService technical interview briefing generation."""
    provider = MockLLMProvider()
    skills = [
        StudentSkill(
            firebase_uid="usr_alpha_12345",
            skill_name="PostgreSQL",
            category="Database",
            confidence_score=0.85,
        )
    ]
    req = InterviewPrepRequest(
        target_role="Backend Engineer",
        company_name="Zerodha",
        focus_skills=["PostgreSQL"],
    )

    res = await career_task_service.generate_interview_prep(provider, skills, req)
    assert isinstance(res, InterviewPrepResponse)
    assert len(res.technical_questions) > 0


@pytest.mark.asyncio
async def test_ai_endpoints_unauthorized(async_client: AsyncClient):
    """Test AI endpoints require valid Firebase token."""
    res = await async_client.post("/api/v1/ai/resume/tailor", json={"target_role": "Backend", "bullet_points": ["API"]})
    assert res.status_code == 401

    res = await async_client.post("/api/v1/ai/roadmap/generate", json={"target_role": "Backend"})
    assert res.status_code == 401

    res = await async_client.post("/api/v1/ai/interview/prep", json={"target_role": "Backend"})
    assert res.status_code == 401

    res = await async_client.post("/api/v1/ai/benchmark")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_ai_health_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/ai/health reports hardware and model status."""
    res = await async_client.get("/api/v1/ai/health")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "model_id" in data
    assert "is_ready" in data
    assert "cuda_available" in data
    assert "vram_allocated_mb" in data


@pytest.mark.asyncio
async def test_ai_resume_tailor_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/ai/resume/tailor authenticated endpoint."""
    payload = {
        "target_role": "Backend Engineer",
        "bullet_points": ["Created REST APIs for payment service."],
        "job_description": "FastAPI, PostgreSQL, microservices",
    }
    res = await async_client.post(
        "/api/v1/ai/resume/tailor",
        json=payload,
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert "tailored_summary" in data
    assert len(data["bullet_points"]) > 0
    assert "impact_metric" in data["bullet_points"][0]


@pytest.mark.asyncio
async def test_ai_roadmap_generate_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/ai/roadmap/generate authenticated endpoint."""
    payload = {
        "target_role": "Backend Engineer",
        "focus_skills": ["Docker", "Redis"],
        "weekly_hours_available": 14,
    }
    res = await async_client.post(
        "/api/v1/ai/roadmap/generate",
        json=payload,
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert "weekly_modules" in data
    assert len(data["weekly_modules"]) > 0
    assert "focus_skill" in data["weekly_modules"][0]


@pytest.mark.asyncio
async def test_ai_interview_prep_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/ai/interview/prep authenticated endpoint."""
    payload = {
        "target_role": "Backend Engineer",
        "company_name": "Razorpay",
        "focus_skills": ["FastAPI", "PostgreSQL"],
    }
    res = await async_client.post(
        "/api/v1/ai/interview/prep",
        json=payload,
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert "technical_questions" in data
    assert len(data["technical_questions"]) > 0
    assert "expected_answer_points" in data["technical_questions"][0]


@pytest.mark.asyncio
async def test_ai_benchmark_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/ai/benchmark endpoint measures performance."""
    res = await async_client.post("/api/v1/ai/benchmark", headers=USER_A_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["task_name"] == "resume_tailor"
    assert data["structured_output_valid"] is True
    assert data["latency_seconds"] >= 0.0
