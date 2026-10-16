"""Endpoints for querying extracted student skills and the knowledge graph."""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.skill import SkillGraphEdge, StudentSkill
from app.schemas.skill import (
    SkillGraphEdgeResponse,
    SkillGraphNode,
    SkillGraphResponse,
    StudentSkillResponse,
)

logger = logging.getLogger("kuru.skills")
router = APIRouter()


@router.get(
    "",
    response_model=list[StudentSkillResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Extracted Student Skills",
    description="Retrieve all verified, evidence-backed skills extracted from code repositories for the current student.",
)
async def get_my_skills(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StudentSkillResponse]:
    """Retrieve all student skills with evidence references strictly isolated to the user."""
    stmt = (
        select(StudentSkill)
        .where(StudentSkill.firebase_uid == current_user.uid)
        .order_by(StudentSkill.confidence_score.desc())
    )
    result = await db.execute(stmt)
    skills = result.scalars().all()
    return [StudentSkillResponse.model_validate(s) for s in skills]


@router.get(
    "/graph",
    response_model=SkillGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Student Skill Knowledge Graph",
    description="Retrieve the complete skill graph with nodes, relationships, and confidence metrics.",
)
async def get_my_skill_graph(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillGraphResponse:
    """Retrieve knowledge graph nodes and relationship edges for the authenticated student."""
    # 1. Fetch skills (nodes)
    stmt_skills = select(StudentSkill).where(StudentSkill.firebase_uid == current_user.uid)
    skills = (await db.execute(stmt_skills)).scalars().all()

    nodes = [
        SkillGraphNode(
            id=s.skill_name,
            name=s.skill_name,
            category=s.category,
            confidence_score=s.confidence_score,
            evidence_count=len(s.evidence),
            repo_count=len(s.source_repositories),
        )
        for s in skills
    ]

    # 2. Fetch edges
    stmt_edges = select(SkillGraphEdge).where(SkillGraphEdge.firebase_uid == current_user.uid)
    edges = (await db.execute(stmt_edges)).scalars().all()

    edge_responses = [
        SkillGraphEdgeResponse(
            source=e.source_skill,
            target=e.target_skill,
            relationship_type=e.relationship_type,
            weight=e.weight,
        )
        for e in edges
    ]

    return SkillGraphResponse(
        nodes=nodes,
        edges=edge_responses,
        total_skills=len(nodes),
        total_relationships=len(edge_responses),
    )
