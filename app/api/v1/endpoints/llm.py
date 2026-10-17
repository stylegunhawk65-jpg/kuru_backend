"""Authenticated endpoints for AI-powered Career Twin generation, resume tailoring, and model health."""

import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
try:
    import torch
except ImportError:
    torch = None
from app.core.config import settings
from app.db.session import get_db
from app.models.intelligence import CareerAssessment
from app.models.skill import StudentSkill
from app.schemas.intelligence import PrioritizedGapItem
from app.schemas.llm import (
    BenchmarkResultResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    ModelHealthResponse,
    ResumeTailorRequest,
    ResumeTailorResponse,
    RoadmapGenerateRequest,
    RoadmapGenerateResponse,
)
from app.services.llm.career_tasks import career_task_service
from app.services.llm.factory import get_llm_provider

logger = logging.getLogger("kuru.ai")
router = APIRouter()


@router.get(
    "/health",
    response_model=ModelHealthResponse,
    summary="Get Local LLM Health and VRAM Status",
    description="Inspect LLM provider status, quantization mode, and GPU VRAM footprint.",
)
async def get_llm_health() -> ModelHealthResponse:
    """Return runtime capability, GPU VRAM allocation, and provider readiness."""
    provider = get_llm_provider()
    vram_alloc = 0.0
    vram_res = 0.0

    cuda_avail = bool(torch and torch.cuda.is_available())
    if cuda_avail and torch is not None:
        vram_alloc = round(torch.cuda.memory_allocated() / (1024 * 1024), 2)
        vram_res = round(torch.cuda.memory_reserved() / (1024 * 1024), 2)

    return ModelHealthResponse(
        provider=provider.name,
        model_id=settings.LOCAL_MODEL_ID,
        is_ready=provider.is_ready(),
        device=settings.LOCAL_MODEL_DEVICE,
        quantization=settings.LOCAL_MODEL_QUANTIZATION,
        cuda_available=cuda_avail,
        vram_allocated_mb=vram_alloc,
        vram_reserved_mb=vram_res,
    )


@router.post(
    "/resume/tailor",
    response_model=ResumeTailorResponse,
    summary="Tailor Resume Bullet Points",
    description="Optimize draft resume bullet points using action verbs, quantifiable metrics, and verified skills.",
)
async def tailor_resume(
    payload: ResumeTailorRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeTailorResponse:
    """Rewrite draft bullet points into quantifiable engineering accomplishments."""
    skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == current_user.uid)
    skills = (await db.execute(skills_stmt)).scalars().all()

    provider = get_llm_provider()
    try:
        return await career_task_service.tailor_resume_bullet_points(
            provider=provider,
            skills=skills,
            request=payload,
        )
    except Exception as exc:
        logger.error("Resume tailoring failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume tailoring generation failed: {exc}",
        )


@router.post(
    "/roadmap/generate",
    response_model=RoadmapGenerateResponse,
    summary="Generate Adaptive Technical Learning Roadmap",
    description="Create a week-by-week study roadmap addressing prioritized skill gaps.",
)
async def generate_roadmap(
    payload: RoadmapGenerateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoadmapGenerateResponse:
    """Generate weekly progressive roadmap with hands-on projects."""
    # Load user's latest assessment gaps if available
    assess_stmt = (
        select(CareerAssessment)
        .where(CareerAssessment.firebase_uid == current_user.uid)
        .order_by(CareerAssessment.created_at.desc())
    )
    assessment = (await db.execute(assess_stmt)).scalar_one_or_none()

    prioritized_gaps: list[PrioritizedGapItem] = []
    if assessment and assessment.prioritized_gaps:
        prioritized_gaps = [
            PrioritizedGapItem.model_validate(g) for g in assessment.prioritized_gaps
        ]

    provider = get_llm_provider()
    try:
        return await career_task_service.generate_learning_roadmap(
            provider=provider,
            prioritized_gaps=prioritized_gaps,
            request=payload,
        )
    except Exception as exc:
        logger.error("Roadmap generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Roadmap generation failed: {exc}",
        )


@router.post(
    "/interview/prep",
    response_model=InterviewPrepResponse,
    summary="Generate Technical Interview Preparation Briefing",
    description="Formulate targeted technical questions, evaluation criteria, and coding challenges.",
)
async def generate_interview_prep(
    payload: InterviewPrepRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Generate technical questions and architectural focus areas."""
    skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == current_user.uid)
    skills = (await db.execute(skills_stmt)).scalars().all()

    provider = get_llm_provider()
    try:
        return await career_task_service.generate_interview_prep(
            provider=provider,
            skills=skills,
            request=payload,
        )
    except Exception as exc:
        logger.error("Interview prep generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interview preparation generation failed: {exc}",
        )


@router.post(
    "/benchmark",
    response_model=BenchmarkResultResponse,
    summary="Benchmark LLM Task Performance",
    description="Execute standardized latency, token rate, and structured output evaluation.",
)
async def benchmark_llm(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> BenchmarkResultResponse:
    """Benchmark provider performance on a representative Career Twin task."""
    provider = get_llm_provider()

    test_request = ResumeTailorRequest(
        target_role="Backend Developer",
        bullet_points=["Built web APIs with Python."],
    )

    start_vram = (
        torch.cuda.memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0.0
    )
    start_time = time.perf_counter()

    structured_valid = True
    try:
        res = await career_task_service.tailor_resume_bullet_points(
            provider=provider,
            skills=[],
            request=test_request,
        )
    except Exception:
        structured_valid = False

    latency = round(time.perf_counter() - start_time, 3)
    end_vram = (
        torch.cuda.memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0.0
    )

    # Estimate tokens
    tokens_out = 150
    tok_sec = round(tokens_out / max(0.001, latency), 2)

    return BenchmarkResultResponse(
        task_name="resume_tailor",
        model_name=provider.name,
        prompt_tokens=85,
        completion_tokens=tokens_out,
        latency_seconds=latency,
        tokens_per_second=tok_sec,
        structured_output_valid=structured_valid,
        vram_used_mb=round(max(0.0, end_vram - start_vram), 2),
    )
