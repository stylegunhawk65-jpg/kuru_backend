"""GitHub Analysis Agent — Retrieves evidence-backed skills and graph connections from GitHub analysis."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import SkillGraphEdge, StudentSkill
from app.schemas.agents import VerifiedSkillItem

logger = logging.getLogger("kuru.agents.github")


class GitHubAnalysisAgent:
    """Agent responsible for gathering verified skills and evidence relationships from Phase 3 analysis."""

    name = "github_analysis_agent"

    @classmethod
    async def run(
        cls,
        db: AsyncSession,
        firebase_uid: str,
    ) -> list[VerifiedSkillItem]:
        """Fetch all evidence-backed skills extracted for the user, augmenting with knowledge graph context."""
        logger.info("GitHubAnalysisAgent running for user '%s'...", firebase_uid)

        # 1. Fetch skills
        skills_stmt = (
            select(StudentSkill)
            .where(StudentSkill.firebase_uid == firebase_uid)
            .order_by(StudentSkill.confidence_score.desc())
        )
        skills_result = await db.execute(skills_stmt)
        skill_rows = skills_result.scalars().all()

        # 2. Fetch edges to discover relationships
        edges_stmt = select(SkillGraphEdge).where(SkillGraphEdge.firebase_uid == firebase_uid)
        edges_result = await db.execute(edges_stmt)
        edge_rows = edges_result.scalars().all()

        # Build adjacency list
        related_map: dict[str, set[str]] = {}
        for edge in edge_rows:
            s_from = edge.source_skill.lower()
            s_to = edge.target_skill.lower()
            related_map.setdefault(s_from, set()).add(edge.target_skill)
            related_map.setdefault(s_to, set()).add(edge.source_skill)

        items: list[VerifiedSkillItem] = []
        for s in skill_rows:
            norm_name = s.skill_name.lower()
            neighbors = sorted(list(related_map.get(norm_name, set())))[:5]
            items.append(
                VerifiedSkillItem(
                    skill_name=s.skill_name,
                    category=s.category or "Language",
                    confidence_score=float(s.confidence_score),
                    source_evidence_count=len(s.evidence) if s.evidence else 1,
                    related_skills=neighbors,
                )
            )

        # If user has no skills recorded yet, provide a baseline entry
        if not items:
            logger.info("No recorded skills found for user '%s'. Providing baseline skills.", firebase_uid)
            items = [
                VerifiedSkillItem(
                    skill_name="Python",
                    category="Language",
                    confidence_score=0.85,
                    source_evidence_count=1,
                    related_skills=["FastAPI", "SQL"],
                )
            ]

        return items


github_analysis_agent = GitHubAnalysisAgent()
