"""Project Recommendation Agent — Recommends portfolio-grade projects tied to skill gaps and target jobs."""

import logging
from app.schemas.agents import ProjectRecommendationItem
from app.services.llm.base import BaseLLMProvider
from app.services.llm.career_tasks import career_task_service

logger = logging.getLogger("kuru.agents.projects")


class ProjectRecommendationAgent:
    """Agent that formulates impactful, portfolio-grade project recommendations targeting candidate gaps."""

    name = "project_recommendation_agent"

    @classmethod
    async def run(
        cls,
        provider: BaseLLMProvider,
        target_role: str,
        skill_gaps: list[str],
        verified_skills: list[str],
        matched_job_titles: list[str] | None = None,
        selected_job_required_skills: list[str] | None = None,
    ) -> list[ProjectRecommendationItem]:
        """Synthesize actionable engineering project recommendations closing verified skill gaps."""
        logger.info(
            "ProjectRecommendationAgent running for role '%s' with %d gaps...",
            target_role,
            len(skill_gaps),
        )

        res = await career_task_service.recommend_portfolio_projects(
            provider=provider,
            target_role=target_role,
            skill_gaps=skill_gaps,
            verified_skills=verified_skills,
            matched_job_titles=matched_job_titles,
            selected_job_required_skills=selected_job_required_skills,
        )

        return res.recommended_projects


project_recommendation_agent = ProjectRecommendationAgent()
