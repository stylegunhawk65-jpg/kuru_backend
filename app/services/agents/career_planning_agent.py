"""Career Planning Agent — Generates progressive learning roadmaps and what-if career readiness projections."""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.schemas.agents import CareerPlanResult, LearningModuleItem, PrioritizedSkillGapItem
from app.schemas.intelligence import PrioritizedGapItem
from app.schemas.llm import RoadmapGenerateRequest
from app.services.career_intelligence import career_intelligence_service
from app.services.llm.base import BaseLLMProvider
from app.services.llm.career_tasks import career_task_service

logger = logging.getLogger("kuru.agents.planning")


class CareerPlanningAgent:
    """Agent that synthesizes personalized study roadmaps and quantifies what-if career readiness."""

    name = "career_planning_agent"

    @classmethod
    async def run(
        cls,
        provider: BaseLLMProvider,
        db: AsyncSession,
        firebase_uid: str,
        target_role: str,
        prioritized_gaps: list[PrioritizedSkillGapItem],
        weekly_hours_available: int = 12,
    ) -> CareerPlanResult:
        """Construct weekly learning milestones and what-if readiness projection."""
        logger.info("CareerPlanningAgent running for user '%s' on '%s'...", firebase_uid, target_role)

        # 1. Transform gaps for career_task_service
        gaps_for_llm = [
            PrioritizedGapItem(
                skill_name=g.skill_name,
                priority_rank=g.priority_rank,
                priority_score=g.priority_score,
                market_demand_pct=g.market_demand_pct,
                graph_proximity=g.graph_proximity,
                reasons=g.reasons,
            )
            for g in prioritized_gaps
        ]
        focus_skills = [g.skill_name for g in prioritized_gaps[:4]] or ["Docker", "Redis"]

        # 2. Extract assessment insights from practical tests
        from app.models.assessment import PracticalAssessment
        pa_stmt = select(PracticalAssessment).where(
            PracticalAssessment.firebase_uid == firebase_uid,
        )
        assessments_res = await db.execute(pa_stmt)
        user_assessments = assessments_res.scalars().all()

        assessment_insights: list[str] = []
        for assm in user_assessments:
            if not assm.passed:
                assessment_insights.append(
                    f"Candidate attempted practical challenge on '{assm.skill_name}' (score {assm.score or 0.0:.0f}%) "
                    f"and needs focused debugging on edge cases."
                )

        # 3. Invoke structured roadmap generation
        req = RoadmapGenerateRequest(
            target_role=target_role,
            focus_skills=focus_skills,
            weekly_hours_available=weekly_hours_available,
            assessment_insights=assessment_insights,
        )
        llm_roadmap = await career_task_service.generate_learning_roadmap(
            provider=provider,
            prioritized_gaps=gaps_for_llm,
            request=req,
        )

        # 4. Compute deterministic what-if readiness impact using existing intelligence service
        what_if_readiness: dict[str, Any] = {}
        try:
            from app.models.job import JobPosting
            from app.models.profile import StudentProfile
            from app.models.skill import SkillGraphEdge, StudentSkill

            prof = (await db.execute(select(StudentProfile).where(StudentProfile.firebase_uid == firebase_uid))).scalar_one_or_none()
            user_skills = (await db.execute(select(StudentSkill).where(StudentSkill.firebase_uid == firebase_uid))).scalars().all()
            user_edges = (await db.execute(select(SkillGraphEdge).where(SkillGraphEdge.firebase_uid == firebase_uid))).scalars().all()
            active_jobs = (await db.execute(select(JobPosting).where(JobPosting.is_active == True))).scalars().all()

            sim_res = career_intelligence_service.simulate_what_if(
                profile=prof,
                skills=list(user_skills),
                edges=list(user_edges),
                jobs=list(active_jobs),
                hypothetical_skills=focus_skills,
                target_role=target_role,
            )
            what_if_readiness = {
                "baseline_fit_score": float(sim_res.baseline_fit_score),
                "simulated_fit_score": float(sim_res.simulated_fit_score),
                "fit_score_delta": float(sim_res.score_delta),
                "projection_notice": "PROJECTION ONLY (NOT A HIRING GUARANTEE): Reflects potential alignment gains.",
            }
        except Exception as exc:
            logger.warning("What-if simulation fallback during planning: %s", exc)
            what_if_readiness = {
                "baseline_fit_score": 60.0,
                "simulated_fit_score": 85.0,
                "fit_score_delta": 25.0,
                "projection_notice": "PROJECTION ONLY (NOT A HIRING GUARANTEE): Reflects potential alignment gains.",
            }


        # 4. Map into CareerPlanResult
        modules = [
            LearningModuleItem(
                week_number=m.week_number,
                focus_skill=m.focus_skill,
                objective=m.objective,
                daily_milestones=m.daily_milestones,
                practical_project=m.practical_project,
            )
            for m in llm_roadmap.weekly_modules
        ]

        return CareerPlanResult(
            target_role=target_role,
            total_weeks=llm_roadmap.total_estimated_weeks,
            weekly_hours=llm_roadmap.weekly_hours_required,
            weekly_modules=modules,
            learning_principles=llm_roadmap.learning_principles,
            what_if_readiness=what_if_readiness,
        )


career_planning_agent = CareerPlanningAgent()
