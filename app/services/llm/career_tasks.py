"""Career Twin specialized task services leveraging structured LLM generation."""

import logging
from typing import Any
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
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger("kuru.llm.tasks")


class CareerTaskService:
    """Specialized orchestrator for Career Twin structured generation tasks."""

    @staticmethod
    async def tailor_resume_bullet_points(
        provider: BaseLLMProvider,
        skills: list[StudentSkill],
        request: ResumeTailorRequest,
    ) -> ResumeTailorResponse:
        """Rewrite resume bullet points emphasizing verified skills and quantifiable metrics."""
        verified_skills_str = ", ".join(
            f"{s.skill_name} ({s.category}, conf={s.confidence_score:.2f})"
            for s in skills
        ) or "None recorded"

        bullet_points_str = "\n".join(f"- {b}" for b in request.bullet_points)

        system_prompt = (
            "You are an expert technical career advisor for software engineering students. "
            "Your objective is to rewrite draft resume bullet points into high-impact, quantifiable "
            "engineering accomplishments using action verbs (e.g. 'Architected', 'Engineered', 'Optimized'). "
            "STRICT PRIVACY & ACCURACY PRINCIPLE: NEVER invent skills or achievements the candidate does not have. "
            "Exclusively incorporate verified skills."
        )

        user_prompt = (
            f"Candidate Verified Skills:\n{verified_skills_str}\n\n"
            f"Target Role: {request.target_role}\n"
            f"Job Description Keywords / Context:\n{request.job_description or 'Standard software engineering requirements'}\n\n"
            f"Draft Bullet Points to Optimize:\n{bullet_points_str}\n\n"
            f"Please transform each bullet point into an achievement-oriented statement with quantifiable impact metrics."
        )

        return await provider.generate_structured(
            prompt=user_prompt,
            schema=ResumeTailorResponse,
            system_prompt=system_prompt,
            max_tokens=650,
            temperature=0.2,
        )

    @staticmethod
    async def generate_learning_roadmap(
        provider: BaseLLMProvider,
        prioritized_gaps: list[PrioritizedGapItem],
        request: RoadmapGenerateRequest,
    ) -> RoadmapGenerateResponse:
        """Construct a progressive weekly narrative learning roadmap."""
        if request.focus_skills:
            skills_to_study = request.focus_skills
        else:
            skills_to_study = [g.skill_name for g in prioritized_gaps[:4]] or ["Git", "Docker", "REST APIs"]

        skills_str = ", ".join(skills_to_study)

        system_prompt = (
            "You are a senior engineering mentor constructing an intensive, project-based study plan. "
            "Focus on practical implementation, hands-on building, and portfolio deliverables. "
            "Avoid passive learning recommendations."
        )

        assessment_ctx = (
            f"Practical Assessment Focus/Weaknesses: {'; '.join(request.assessment_insights)}\n"
            if request.assessment_insights
            else ""
        )

        user_prompt = (
            f"Target Role: {request.target_role}\n"
            f"Priority Skills to Master: {skills_str}\n"
            f"Weekly Dedicated Hours: {request.weekly_hours_available} hours/week\n"
            f"{assessment_ctx}\n"
            f"Generate a progressive weekly roadmap with concrete daily milestones and a portfolio deliverable."
        )

        return await provider.generate_structured(
            prompt=user_prompt,
            schema=RoadmapGenerateResponse,
            system_prompt=system_prompt,
            max_tokens=650,
            temperature=0.2,
        )

    @staticmethod
    async def generate_interview_prep(
        provider: BaseLLMProvider,
        skills: list[StudentSkill],
        request: InterviewPrepRequest,
    ) -> InterviewPrepResponse:
        """Generate tailored technical questions, coding challenges, and interview guidance."""
        skills_str = ", ".join(request.focus_skills or [s.skill_name for s in skills[:6]]) or "Python, SQL"

        system_prompt = (
            "You are a technical hiring manager at a top technology company. "
            "Formulate challenging, in-depth architectural and technical questions tailored to the candidate's skills "
            "and target role. Include rigorous evaluation rubric points."
        )

        user_prompt = (
            f"Target Role: {request.target_role}\n"
            f"Target Company Focus: {request.company_name or 'General Tech Ecosystem'}\n"
            f"Focus Skills: {skills_str}\n\n"
            f"Generate targeted technical questions, expected answer criteria, coding challenge topics, and behavioral guidance."
        )

        return await provider.generate_structured(
            prompt=user_prompt,
            schema=InterviewPrepResponse,
            system_prompt=system_prompt,
            max_tokens=650,
            temperature=0.3,
        )

    @staticmethod
    async def recommend_portfolio_projects(
        provider: BaseLLMProvider,
        target_role: str,
        skill_gaps: list[str],
        verified_skills: list[str],
        matched_job_titles: list[str] | None = None,
        selected_job_required_skills: list[str] | None = None,
    ) -> Any:
        """Synthesize concrete portfolio projects directly targeting candidate skill gaps and validate against job technologies."""
        from app.schemas.agents import ProjectRecommendationsResponse
        from app.services.matcher import normalize_skill

        gaps_str = ", ".join(skill_gaps[:5]) or "Docker, Redis, System Design"
        existing_str = ", ".join(verified_skills[:5]) or "Python, SQL"
        jobs_context = f" Target Job Alignments: {', '.join(matched_job_titles[:3])}." if matched_job_titles else ""
        if selected_job_required_skills:
            jobs_context += f" Selected Job Required Skills: {', '.join(selected_job_required_skills)}."

        system_prompt = (
            "You are a technical hiring manager and staff software architect. "
            "Recommend 2 impactful, portfolio-grade projects that demonstrate production competencies in missing skills. "
            "Focus on real-world engineering value, runnable code, and measurable performance."
        )

        user_prompt = (
            f"Target Role: {target_role}\n"
            f"Identified Priority Skill Gaps: {gaps_str}\n"
            f"Candidate Verified Foundation: {existing_str}\n{jobs_context}\n\n"
            f"Recommend concrete engineering projects that directly close these gaps and prove readiness."
        )

        res: ProjectRecommendationsResponse = await provider.generate_structured(
            prompt=user_prompt,
            schema=ProjectRecommendationsResponse,
            system_prompt=system_prompt,
            max_tokens=650,
            temperature=0.3,
        )

        # Validate each project's tech_stack against target job requirements and skill gaps
        target_skills_set = {normalize_skill(s) for s in (selected_job_required_skills or skill_gaps)}
        for proj in res.recommended_projects:
            validated = [
                tech for tech in proj.tech_stack
                if normalize_skill(tech) in target_skills_set or any(normalize_skill(tech) in s for s in target_skills_set)
            ]
            proj.validated_job_technologies = validated
            if validated:
                proj.job_alignment_summary = (
                    f"Directly exercises {len(validated)} required technologies ({', '.join(validated)}) "
                    f"critical for the target job role."
                )
            else:
                proj.job_alignment_summary = (
                    f"Builds core architecture foundations supporting {', '.join(proj.target_skill_gaps)}."
                )

        return res


career_task_service = CareerTaskService()
