"""Authenticated Practical Assessment endpoints: adaptive challenge generation, isolated submission evaluation, and results."""

from datetime import datetime, timezone
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.assessment import AssessmentSubmission, PracticalAssessment
from app.schemas.assessment import (
    AssessmentPublicResponse,
    CreateAssessmentRequest,
    PracticalAssessmentListItem,
    SubmitSolutionRequest,
    SubmitSolutionResponse,
)
from app.services.assessments.generator import challenge_generator
from app.services.assessments.service import assessment_service

logger = logging.getLogger("kuru.api.assessments")
router = APIRouter()


@router.post(
    "",
    response_model=AssessmentPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Practical Skill Assessment",
    description="Adaptively select challenge level and generate repository-grounded practical challenge with public/hidden tests.",
)
async def create_assessment(
    payload: CreateAssessmentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentPublicResponse:
    """Create a practical assessment and return public challenge specification."""
    assessment = await assessment_service.create_assessment(
        db=db,
        firebase_uid=current_user.uid,
        skill_name=payload.skill_name,
        repository_id=payload.repository_id,
        forced_level=payload.forced_level,
    )
    public_data = await assessment_service.get_challenge_public(
        db=db,
        firebase_uid=current_user.uid,
        assessment_id=assessment.id,
    )
    return AssessmentPublicResponse.model_validate(public_data)


@router.get(
    "/{assessment_id}/challenge",
    response_model=AssessmentPublicResponse,
    summary="Get Assessment Challenge Specification",
    description="Retrieve the active challenge specification with hidden tests strictly stripped.",
)
async def get_challenge(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentPublicResponse:
    """Retrieve public challenge details for student UI."""
    public_data = await assessment_service.get_challenge_public(
        db=db,
        firebase_uid=current_user.uid,
        assessment_id=assessment_id,
    )
    return AssessmentPublicResponse.model_validate(public_data)


@router.post(
    "/{assessment_id}/submit",
    response_model=SubmitSolutionResponse,
    summary="Submit Assessment Solution",
    description="Execute solution in secure isolated sandbox against public and hidden tests; evaluate rubric and update Career Twin skills.",
)
async def submit_solution(
    assessment_id: str,
    payload: SubmitSolutionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmitSolutionResponse:
    """Evaluate student submission in sandbox and persist results."""
    result = await assessment_service.submit_solution(
        db=db,
        firebase_uid=current_user.uid,
        assessment_id=assessment_id,
        submitted_code=payload.submitted_code,
    )
    return SubmitSolutionResponse.model_validate(result)


@router.get(
    "/{assessment_id}/results",
    summary="Get Assessment Results & Submission History",
    description="Retrieve comprehensive assessment status, scores, rubric feedback, and attempt history.",
)
async def get_assessment_results(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve assessment details and all submission attempts with strict per-user isolation."""
    stmt = (
        select(PracticalAssessment)
        .options(selectinload(PracticalAssessment.submissions))
        .where(
            PracticalAssessment.id == assessment_id,
            PracticalAssessment.firebase_uid == current_user.uid,
        )
    )
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    submissions_list = [
        {
            "id": s.id,
            "attempt_number": s.attempt_number,
            "execution_status": s.execution_status,
            "score": s.score,
            "public_results": s.public_results,
            "hidden_results": s.hidden_results,
            "rubric_feedback": s.rubric_feedback,
            "execution_metrics": s.execution_metrics,
            "created_at": s.created_at,
        }
        for s in assessment.submissions
    ]

    return {
        "assessment_id": assessment.id,
        "skill_name": assessment.skill_name,
        "assessment_level": assessment.assessment_level,
        "challenge_type": assessment.challenge_type,
        "status": assessment.status,
        "attempt_count": assessment.attempt_count,
        "max_attempts": assessment.max_attempts,
        "score": assessment.score,
        "passed": assessment.passed,
        "level_selection_rationale": assessment.level_selection_rationale,
        "submissions": submissions_list,
        "created_at": assessment.created_at,
        "completed_at": assessment.completed_at,
    }


@router.post(
    "/{assessment_id}/reassess",
    response_model=AssessmentPublicResponse,
    summary="Request Challenge Variation / Reassessment",
    description="Generate a fresh challenge variation if attempts are available.",
)
async def request_reassessment(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentPublicResponse:
    """Regenerate challenge variation within existing attempt bounds."""
    stmt = select(PracticalAssessment).where(
        PracticalAssessment.id == assessment_id,
        PracticalAssessment.firebase_uid == current_user.uid,
    )
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    if assessment.attempt_count >= assessment.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum attempts exceeded. Please initiate a new assessment.",
        )

    if assessment.passed is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment already passed. Skill is practically demonstrated.",
        )

    # Generate new challenge variation
    new_challenge = await challenge_generator.generate_challenge(
        skill_name=assessment.skill_name,
        level=assessment.assessment_level,
        challenge_type=assessment.challenge_type,
    )

    public_challenge = {
        "title": new_challenge["title"],
        "description": new_challenge["description"],
        "entry_function": new_challenge["entry_function"],
        "starter_code": new_challenge["starter_code"],
        "public_tests": new_challenge.get("public_tests", []),
        "difficulty": new_challenge["difficulty"],
        "rubric": new_challenge.get("rubric", {}),
    }

    assessment.challenge_data = public_challenge
    assessment.hidden_test_data = new_challenge.get("hidden_tests", [])
    assessment.status = "in_progress"
    await db.commit()
    await db.refresh(assessment)

    public_data = await assessment_service.get_challenge_public(
        db=db,
        firebase_uid=current_user.uid,
        assessment_id=assessment.id,
    )
    return AssessmentPublicResponse.model_validate(public_data)


@router.get(
    "",
    response_model=list[PracticalAssessmentListItem],
    summary="List Practical Assessments",
    description="List all past and active practical assessments for the authenticated user.",
)
async def list_assessments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PracticalAssessmentListItem]:
    """List assessments enforcing strict per-user isolation."""
    offset = (page - 1) * per_page
    stmt = (
        select(PracticalAssessment)
        .where(PracticalAssessment.firebase_uid == current_user.uid)
        .order_by(PracticalAssessment.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    assessments = (await db.execute(stmt)).scalars().all()

    return [
        PracticalAssessmentListItem(
            id=a.id,
            skill_name=a.skill_name,
            assessment_level=a.assessment_level,
            challenge_type=a.challenge_type,
            status=a.status,
            attempt_count=a.attempt_count,
            max_attempts=a.max_attempts,
            score=a.score,
            passed=a.passed,
            created_at=a.created_at,
            completed_at=a.completed_at,
        )
        for a in assessments
    ]


@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Practical Assessment",
    description="Delete an assessment and its submissions.",
)
async def delete_assessment(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete assessment with strict user isolation."""
    stmt = select(PracticalAssessment).where(
        PracticalAssessment.id == assessment_id,
        PracticalAssessment.firebase_uid == current_user.uid,
    )
    assessment = (await db.execute(stmt)).scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )

    await db.delete(assessment)
    await db.commit()
