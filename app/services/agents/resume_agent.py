"""Resume Agent — Tailors engineering resume achievements using verified skills and target job context."""

import logging
from typing import Any
from app.models.skill import StudentSkill
from app.schemas.agents import TailoredResumeResult
from app.schemas.llm import ResumeTailorRequest
from app.services.llm.base import BaseLLMProvider
from app.services.llm.career_tasks import career_task_service

logger = logging.getLogger("kuru.agents.resume")


class ResumeAgent:
    """Agent that tailors resume bullet points with action verbs, verified skills, and quantifiable impact."""

    name = "resume_agent"

    @classmethod
    async def run(
        cls,
        provider: BaseLLMProvider,
        target_role: str,
        bullet_points: list[str],
        verified_skills: list[str],
        job_description: str | None = None,
    ) -> TailoredResumeResult:
        """Execute resume tailoring using verified skills and target job description."""
        logger.info("ResumeAgent running for role '%s'...", target_role)

        skills_objects = [
            StudentSkill(
                firebase_uid="agent_ctx",
                skill_name=s,
                category="Language",
                confidence_score=0.9,
            )
            for s in verified_skills
        ]

        # Use default draft bullets if none provided
        drafts = bullet_points or [
            "Built REST APIs using Python and database storage.",
            "Handled backend services and deployment configuration.",
        ]

        req = ResumeTailorRequest(
            target_role=target_role,
            bullet_points=drafts,
            job_description=job_description,
        )

        res = await career_task_service.tailor_resume_bullet_points(
            provider=provider,
            skills=skills_objects,
            request=req,
        )

        bullets: list[dict[str, Any]] = [
            {
                "original": b.original,
                "tailored": b.tailored,
                "highlighted_skills": b.highlighted_skills,
                "impact_metric": b.impact_metric,
            }
            for b in res.bullet_points
        ]

        return TailoredResumeResult(
            target_role=res.target_role,
            tailored_summary=res.tailored_summary,
            bullet_points=bullets,
            alignment_explanation=res.alignment_explanation,
        )


resume_agent = ResumeAgent()
