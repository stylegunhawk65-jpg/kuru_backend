"""LangGraph workflow orchestration for Career Twin multi-agent pipeline."""

from datetime import datetime, timezone
import logging
from typing import Any, Literal
import uuid
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.agent_workflow import AgentApprovalRequest, AgentWorkflowRun
from app.schemas.agents import CareerTwinAgentState
from app.services.agents.approval_agent import approval_workflow_agent
from app.services.agents.career_planning_agent import career_planning_agent
from app.services.agents.github_agent import github_analysis_agent
from app.services.agents.job_matching_agent import job_matching_agent
from app.services.agents.profile_agent import career_profile_agent
from app.services.agents.project_recommendation_agent import project_recommendation_agent
from app.services.agents.resource_research_agent import resource_research_agent
from app.services.agents.resume_agent import resume_agent
from app.services.agents.skill_gap_agent import skill_gap_agent
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import get_llm_provider

logger = logging.getLogger("kuru.agents.workflow")


class CareerTwinWorkflowService:
    """Orchestrator building and running LangGraph multi-agent pipelines with persistence and human approval gates."""

    def __init__(self, checkpointer: Any | None = None) -> None:
        self.checkpointer = checkpointer or MemorySaver()
        self._compiled_full_graph = None
        self._compiled_roadmap_graph = None

    # ---------------------------------------------------------------------------
    # LangGraph Node Handlers
    # ---------------------------------------------------------------------------

    @staticmethod
    async def profile_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 1: Career Profile Agent."""
        db: AsyncSession = config["configurable"]["db"]
        uid = state["firebase_uid"]
        target_override = state.get("target_role")

        try:
            profile = await career_profile_agent.run(db, uid, target_role_override=target_override)
            return {
                "profile": profile.model_dump(),
                "target_role": profile.primary_target_role,
                "step_history": state["step_history"] + ["profile_node"],
            }
        except Exception as exc:
            logger.error("Error in profile_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"profile_node error: {exc}"],
                "step_history": state["step_history"] + ["profile_node:failed"],
            }

    @staticmethod
    async def github_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 2: GitHub Analysis Agent."""
        db: AsyncSession = config["configurable"]["db"]
        uid = state["firebase_uid"]

        try:
            skills = await github_analysis_agent.run(db, uid)
            return {
                "skills": [s.model_dump() for s in skills],
                "step_history": state["step_history"] + ["github_node"],
            }
        except Exception as exc:
            logger.error("Error in github_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"github_node error: {exc}"],
                "step_history": state["step_history"] + ["github_node:failed"],
            }

    @staticmethod
    async def job_matching_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 3: Job Matching Agent."""
        db: AsyncSession = config["configurable"]["db"]
        uid = state["firebase_uid"]
        role = state.get("target_role") or "Backend Engineer"

        try:
            matched_jobs = await job_matching_agent.run(db, uid, target_role=role, limit=5)
            return {
                "matched_jobs": [j.model_dump() for j in matched_jobs],
                "step_history": state["step_history"] + ["job_matching_node"],
            }
        except Exception as exc:
            logger.error("Error in job_matching_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"job_matching_node error: {exc}"],
                "step_history": state["step_history"] + ["job_matching_node:failed"],
            }

    @staticmethod
    async def skill_gap_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 4: Skill Gap Agent."""
        db: AsyncSession = config["configurable"]["db"]
        uid = state["firebase_uid"]
        role = state.get("target_role") or "Backend Engineer"

        try:
            gaps = await skill_gap_agent.run(db, uid, target_role=role)
            return {
                "skill_gaps": [g.model_dump() for g in gaps],
                "step_history": state["step_history"] + ["skill_gap_node"],
            }
        except Exception as exc:
            logger.error("Error in skill_gap_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"skill_gap_node error: {exc}"],
                "step_history": state["step_history"] + ["skill_gap_node:failed"],
            }

    @staticmethod
    async def career_planning_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 5: Career Planning Agent."""
        db: AsyncSession = config["configurable"]["db"]
        provider: BaseLLMProvider = config["configurable"].get("provider") or get_llm_provider()
        uid = state["firebase_uid"]
        role = state.get("target_role") or "Backend Engineer"
        weekly_hours = state.get("weekly_hours_available", 12)

        from app.schemas.agents import PrioritizedSkillGapItem
        raw_gaps = state.get("skill_gaps", [])
        gaps = [PrioritizedSkillGapItem(**g) for g in raw_gaps]

        try:
            plan = await career_planning_agent.run(
                provider=provider,
                db=db,
                firebase_uid=uid,
                target_role=role,
                prioritized_gaps=gaps,
                weekly_hours_available=weekly_hours,
            )
            return {
                "career_plan": plan.model_dump(),
                "step_history": state["step_history"] + ["career_planning_node"],
            }
        except Exception as exc:
            logger.error("Error in career_planning_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"career_planning_node error: {exc}"],
                "step_history": state["step_history"] + ["career_planning_node:failed"],
            }

    @staticmethod
    async def resource_research_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 6: Resource Research Agent."""
        raw_gaps = state.get("skill_gaps", [])
        gap_names = [g["skill_name"] for g in raw_gaps[:5]] or ["Docker", "Redis"]

        try:
            resources_map = await resource_research_agent.run(skills=gap_names, limit_per_skill=2)
            serialized = {k: [r.model_dump() for r in v] for k, v in resources_map.items()}
            return {
                "resources": serialized,
                "step_history": state["step_history"] + ["resource_research_node"],
            }
        except Exception as exc:
            logger.error("Error in resource_research_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"resource_research_node error: {exc}"],
                "step_history": state["step_history"] + ["resource_research_node:failed"],
            }

    @staticmethod
    async def project_recommendation_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 7: Project Recommendation Agent."""
        provider: BaseLLMProvider = config["configurable"].get("provider") or get_llm_provider()
        role = state.get("target_role") or "Backend Engineer"
        raw_gaps = state.get("skill_gaps", [])
        gap_names = [g["skill_name"] for g in raw_gaps[:4]] or ["Docker", "Redis"]
        raw_skills = state.get("skills", [])
        verified_names = [s["skill_name"] for s in raw_skills[:4]] or ["Python", "FastAPI"]
        matched_jobs = [j["title"] for j in state.get("matched_jobs", [])[:3]]

        target_job_id = state.get("target_job_id")
        selected_job = None
        for j in state.get("matched_jobs", []):
            if target_job_id and j.get("id") == target_job_id:
                selected_job = j
                break
        if not selected_job and state.get("matched_jobs"):
            selected_job = state["matched_jobs"][0]

        job_req_skills = []
        if selected_job:
            job_req_skills = list(dict.fromkeys(selected_job.get("matched_skills", []) + selected_job.get("missing_skills", [])))

        try:
            projects = await project_recommendation_agent.run(
                provider=provider,
                target_role=role,
                skill_gaps=gap_names,
                verified_skills=verified_names,
                matched_job_titles=matched_jobs,
                selected_job_required_skills=job_req_skills or None,
            )
            return {
                "projects": [p.model_dump() for p in projects],
                "step_history": state["step_history"] + ["project_recommendation_node"],
            }
        except Exception as exc:
            logger.error("Error in project_recommendation_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"project_recommendation_node error: {exc}"],
                "step_history": state["step_history"] + ["project_recommendation_node:failed"],
            }

    @staticmethod
    async def resume_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 8: Resume Agent."""
        provider: BaseLLMProvider = config["configurable"].get("provider") or get_llm_provider()
        role = state.get("target_role") or "Backend Engineer"
        raw_skills = state.get("skills", [])
        verified_names = [s["skill_name"] for s in raw_skills[:5]] or ["Python", "FastAPI", "PostgreSQL"]

        # If a target job ID was requested, extract company context
        matched_jobs = state.get("matched_jobs", [])
        job_desc = None
        target_job_id = state.get("target_job_id")
        if target_job_id:
            for j in matched_jobs:
                if j["id"] == target_job_id:
                    job_desc = f"Role: {j['title']} at {j['company']}. Required skills: {', '.join(j.get('missing_skills', []))}"
                    break

        try:
            resume_res = await resume_agent.run(
                provider=provider,
                target_role=role,
                bullet_points=[],
                verified_skills=verified_names,
                job_description=job_desc,
            )
            return {
                "resume": resume_res.model_dump(),
                "step_history": state["step_history"] + ["resume_node"],
            }
        except Exception as exc:
            logger.error("Error in resume_node: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"resume_node error: {exc}"],
                "step_history": state["step_history"] + ["resume_node:failed"],
            }

    @staticmethod
    async def approval_gate_node(state: CareerTwinAgentState, config: RunnableConfig) -> dict[str, Any]:
        """Node 9: Approval Workflow Agent (Human-in-the-loop Gate)."""
        db: AsyncSession = config["configurable"]["db"]
        uid = state["firebase_uid"]
        thread_id = state["thread_id"]
        action = state.get("requested_action")

        if not action or state.get("approval_status") == "approved":
            return {
                "step_history": state["step_history"] + ["approval_gate_node:bypassed_or_approved"],
            }

        # Queue consequential action for human approval
        action_desc = f"Action '{action}' queued by Career Twin agent for user '{uid}'."
        payload = {
            "target_role": state.get("target_role"),
            "target_job_id": state.get("target_job_id"),
            "resume_summary": (state.get("resume") or {}).get("tailored_summary"),
            "projects_count": len(state.get("projects") or []),
        }

        try:
            approval = await approval_workflow_agent.queue_approval_request(
                db=db,
                firebase_uid=uid,
                thread_id=thread_id,
                action_type=action,
                action_description=action_desc,
                payload=payload,
                target_entity_id=state.get("target_job_id"),
            )
            return {
                "pending_approval": {
                    "id": approval.id,
                    "action_type": approval.action_type,
                    "status": approval.status,
                    "description": approval.action_description,
                },
                "approval_status": "pending",
                "step_history": state["step_history"] + ["approval_gate_node:queued"],
            }
        except Exception as exc:
            logger.error("Error queueing approval: %s", exc, exc_info=True)
            return {
                "errors": state["errors"] + [f"approval_gate_node error: {exc}"],
                "step_history": state["step_history"] + ["approval_gate_node:failed"],
            }

    # ---------------------------------------------------------------------------
    # Graph Construction & Compilation
    # ---------------------------------------------------------------------------

    def build_full_career_twin_graph(self) -> Any:
        """Construct the complete 9-agent Career Twin LangGraph pipeline."""
        builder = StateGraph(CareerTwinAgentState)

        # 1. Add all 9 agent nodes
        builder.add_node("career_profile", self.profile_node)
        builder.add_node("github_analysis", self.github_node)
        builder.add_node("job_matching", self.job_matching_node)
        builder.add_node("skill_gap", self.skill_gap_node)
        builder.add_node("career_planning", self.career_planning_node)
        builder.add_node("resource_research", self.resource_research_node)
        builder.add_node("project_recommendation", self.project_recommendation_node)
        builder.add_node("resume", self.resume_node)
        builder.add_node("approval_gate", self.approval_gate_node)

        # 2. Add edges:
        # START -> profile -> github -> jobs -> gaps -> plan -> resources -> projects -> resume -> approval -> END
        builder.add_edge(START, "career_profile")
        builder.add_edge("career_profile", "github_analysis")
        builder.add_edge("github_analysis", "job_matching")
        builder.add_edge("job_matching", "skill_gap")
        builder.add_edge("skill_gap", "career_planning")
        builder.add_edge("career_planning", "resource_research")
        builder.add_edge("resource_research", "project_recommendation")
        builder.add_edge("project_recommendation", "resume")
        builder.add_edge("resume", "approval_gate")
        builder.add_edge("approval_gate", END)

        return builder.compile(checkpointer=self.checkpointer)

    def build_roadmap_subgraph(self) -> Any:
        """Construct focused sub-workflow: skill_gaps -> career_roadmap -> project_recommendations."""
        builder = StateGraph(CareerTwinAgentState)

        builder.add_node("skill_gap", self.skill_gap_node)
        builder.add_node("career_planning", self.career_planning_node)
        builder.add_node("resource_research", self.resource_research_node)
        builder.add_node("project_recommendation", self.project_recommendation_node)

        builder.add_edge(START, "skill_gap")
        builder.add_edge("skill_gap", "career_planning")
        builder.add_edge("career_planning", "resource_research")
        builder.add_edge("resource_research", "project_recommendation")
        builder.add_edge("project_recommendation", END)

        return builder.compile(checkpointer=self.checkpointer)

    # ---------------------------------------------------------------------------
    # Execution Helpers with Persistence & Auditing
    # ---------------------------------------------------------------------------

    async def run_full_workflow(
        self,
        db: AsyncSession,
        firebase_uid: str,
        target_role: str | None = None,
        target_job_id: str | None = None,
        weekly_hours: int = 12,
        action_to_queue: str | None = None,
        provider: BaseLLMProvider | None = None,
    ) -> tuple[str, CareerTwinAgentState]:
        """Execute the full 9-agent Career Twin pipeline with database persistence."""
        if self._compiled_full_graph is None:
            self._compiled_full_graph = self.build_full_career_twin_graph()

        run_id = str(uuid.uuid4())
        thread_id = f"{firebase_uid}:{run_id}"

        # Initialize audit record
        audit_run = AgentWorkflowRun(
            id=run_id,
            firebase_uid=firebase_uid,
            thread_id=thread_id,
            workflow_type="full_career_twin",
            status="running",
            current_step="start",
            state_summary={},
        )
        db.add(audit_run)
        await db.commit()

        initial_state: CareerTwinAgentState = {
            "firebase_uid": firebase_uid,
            "thread_id": thread_id,
            "target_role": target_role or "",
            "target_job_id": target_job_id,
            "weekly_hours_available": weekly_hours,
            "requested_action": action_to_queue,
            "profile": None,
            "skills": [],
            "matched_jobs": [],
            "skill_gaps": [],
            "career_plan": None,
            "resources": {},
            "projects": [],
            "resume": None,
            "pending_approval": None,
            "approval_status": "none",
            "executed_action": None,
            "step_history": ["workflow_initiated"],
            "errors": [],
        }

        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id,
                "db": db,
                "provider": provider or get_llm_provider(),
            },
            "run_name": "kuru_full_career_twin_workflow",
            "tags": [
                "kuru-career-twin",
                "full_career_twin",
                settings.ENVIRONMENT,
            ],
            "metadata": {
                "project": settings.LANGSMITH_PROJECT,
                "workflow_type": "full_career_twin",
                "thread_id": thread_id,
                "run_id": run_id,
                "target_role": target_role or "",
            },
        }

        try:
            final_state = await self._compiled_full_graph.ainvoke(initial_state, config=config)

            # Update audit record
            status = "waiting_approval" if final_state.get("approval_status") == "pending" else "completed"
            audit_run.status = status
            audit_run.current_step = final_state["step_history"][-1] if final_state["step_history"] else "end"
            audit_run.state_summary = {
                "target_role": final_state.get("target_role"),
                "skills_count": len(final_state.get("skills") or []),
                "matched_jobs_count": len(final_state.get("matched_jobs") or []),
                "gaps_count": len(final_state.get("skill_gaps") or []),
                "projects_count": len(final_state.get("projects") or []),
                "approval_status": final_state.get("approval_status"),
                "steps": final_state.get("step_history"),
            }
            if final_state.get("errors"):
                audit_run.error_message = "; ".join(final_state["errors"])

            await db.commit()
            return run_id, final_state

        except Exception as exc:
            logger.error("Workflow failed for '%s': %s", firebase_uid, exc, exc_info=True)
            audit_run.status = "failed"
            audit_run.error_message = str(exc)
            await db.commit()
            raise

    async def run_roadmap_subworkflow(
        self,
        db: AsyncSession,
        firebase_uid: str,
        target_role: str,
        weekly_hours: int = 12,
        provider: BaseLLMProvider | None = None,
    ) -> tuple[str, CareerTwinAgentState]:
        """Execute the focused skill gaps -> roadmap -> project recommendations pipeline."""
        if self._compiled_roadmap_graph is None:
            self._compiled_roadmap_graph = self.build_roadmap_subgraph()

        run_id = str(uuid.uuid4())
        thread_id = f"{firebase_uid}:{run_id}"

        audit_run = AgentWorkflowRun(
            id=run_id,
            firebase_uid=firebase_uid,
            thread_id=thread_id,
            workflow_type="skill_roadmap_project",
            status="running",
            current_step="start",
            state_summary={},
        )
        db.add(audit_run)
        await db.commit()

        initial_state: CareerTwinAgentState = {
            "firebase_uid": firebase_uid,
            "thread_id": thread_id,
            "target_role": target_role,
            "target_job_id": None,
            "weekly_hours_available": weekly_hours,
            "requested_action": None,
            "profile": None,
            "skills": [],
            "matched_jobs": [],
            "skill_gaps": [],
            "career_plan": None,
            "resources": {},
            "projects": [],
            "resume": None,
            "pending_approval": None,
            "approval_status": "none",
            "executed_action": None,
            "step_history": ["subworkflow_initiated"],
            "errors": [],
        }

        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id,
                "db": db,
                "provider": provider or get_llm_provider(),
            },
            "run_name": "kuru_skill_roadmap_project_subworkflow",
            "tags": [
                "kuru-career-twin",
                "skill_roadmap_project",
                settings.ENVIRONMENT,
            ],
            "metadata": {
                "project": settings.LANGSMITH_PROJECT,
                "workflow_type": "skill_roadmap_project",
                "thread_id": thread_id,
                "run_id": run_id,
                "target_role": target_role,
            },
        }

        try:
            final_state = await self._compiled_roadmap_graph.ainvoke(initial_state, config=config)
            audit_run.status = "completed"
            audit_run.current_step = final_state["step_history"][-1]
            audit_run.state_summary = {
                "target_role": final_state.get("target_role"),
                "gaps_count": len(final_state.get("skill_gaps") or []),
                "projects_count": len(final_state.get("projects") or []),
                "steps": final_state.get("step_history"),
            }
            await db.commit()
            return run_id, final_state

        except Exception as exc:
            logger.error("Subworkflow failed: %s", exc, exc_info=True)
            audit_run.status = "failed"
            audit_run.error_message = str(exc)
            await db.commit()
            raise


workflow_service = CareerTwinWorkflowService()
