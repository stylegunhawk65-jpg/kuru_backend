"""Authenticated endpoints for orchestrating multi-agent pipelines, tracking executions, and human approval gates."""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.agent_workflow import AgentApprovalRequest, AgentWorkflowRun
from app.schemas.agents import (
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    WorkflowRunResponse,
    WorkflowTriggerRequest,
)
from app.services.agents.approval_agent import approval_workflow_agent
from app.services.agents.workflow import workflow_service

logger = logging.getLogger("kuru.api.agents")
router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Multi-Agent Workflow Triggers & Execution
# ---------------------------------------------------------------------------

@router.post(
    "/workflows/career-twin",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Trigger end-to-end 9-agent Career Twin pipeline",
)
async def trigger_career_twin_workflow(
    request: WorkflowTriggerRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute the complete 9-agent pipeline:

    profile -> github -> jobs -> skill_gaps -> career_planning ->
    resources -> project_recommendations -> resume -> approval_gate
    """
    logger.info("Triggering full Career Twin workflow for '%s'...", current_user.uid)

    run_id, final_state = await workflow_service.run_full_workflow(
        db=db,
        firebase_uid=current_user.uid,
        target_role=request.target_role,
        target_job_id=request.target_job_id,
        weekly_hours=request.weekly_hours_available,
        action_to_queue=request.consequential_action_requested,
    )

    return {
        "run_id": run_id,
        "thread_id": final_state["thread_id"],
        "target_role": final_state.get("target_role"),
        "approval_status": final_state.get("approval_status"),
        "pending_approval": final_state.get("pending_approval"),
        "state_summary": {
            "skills_count": len(final_state.get("skills") or []),
            "matched_jobs_count": len(final_state.get("matched_jobs") or []),
            "skill_gaps_count": len(final_state.get("skill_gaps") or []),
            "projects_count": len(final_state.get("projects") or []),
            "has_roadmap": bool(final_state.get("career_plan")),
            "has_tailored_resume": bool(final_state.get("resume")),
            "steps": final_state.get("step_history"),
        },
        "career_plan": final_state.get("career_plan"),
        "recommended_projects": final_state.get("projects"),
        "tailored_resume": final_state.get("resume"),
        "genuine_resources": final_state.get("resources"),
    }


@router.post(
    "/workflows/roadmap",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Trigger incremental skill gaps -> roadmap -> project recommendations pipeline",
)
async def trigger_roadmap_subworkflow(
    request: WorkflowTriggerRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute focused sub-workflow: skill_gaps -> career_planning -> resources -> project_recommendation."""
    target_role = request.target_role or "Backend Engineer"
    logger.info("Triggering roadmap subworkflow for user '%s' on '%s'...", current_user.uid, target_role)

    run_id, final_state = await workflow_service.run_roadmap_subworkflow(
        db=db,
        firebase_uid=current_user.uid,
        target_role=target_role,
        weekly_hours=request.weekly_hours_available,
    )

    return {
        "run_id": run_id,
        "thread_id": final_state["thread_id"],
        "target_role": final_state.get("target_role"),
        "skill_gaps": final_state.get("skill_gaps"),
        "career_plan": final_state.get("career_plan"),
        "genuine_resources": final_state.get("resources"),
        "recommended_projects": final_state.get("projects"),
        "step_history": final_state.get("step_history"),
    }


@router.get(
    "/workflows/{run_id}",
    response_model=WorkflowRunResponse,
    summary="Get workflow execution status and audit summary",
)
async def get_workflow_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowRunResponse:
    """Retrieve audit record of a workflow run. Strictly isolated to the user who triggered it."""
    stmt = (
        select(AgentWorkflowRun)
        .where(AgentWorkflowRun.id == run_id)
        .where(AgentWorkflowRun.firebase_uid == current_user.uid)
    )
    result = await db.execute(stmt)
    run = result.scalars().first()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found.",
        )

    return WorkflowRunResponse(
        id=run.id,
        thread_id=run.thread_id,
        workflow_type=run.workflow_type,
        status=run.status,
        current_step=run.current_step,
        state_summary=run.state_summary or {},
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


# ---------------------------------------------------------------------------
# 2. Human-in-the-Loop Approval Gates
# ---------------------------------------------------------------------------

@router.get(
    "/approvals",
    response_model=list[ApprovalRequestResponse],
    summary="List queued approval requests for authenticated student",
)
async def list_approvals(
    status_filter: str | None = Query(None, alias="status", description="Filter by: pending, approved, rejected"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApprovalRequestResponse]:
    """Retrieve queued approval requests strictly isolated to authenticated user."""
    approvals = await approval_workflow_agent.list_user_approvals(
        db=db,
        firebase_uid=current_user.uid,
        status_filter=status_filter,
    )
    return [
        ApprovalRequestResponse(
            id=a.id,
            thread_id=a.thread_id,
            action_type=a.action_type,
            action_description=a.action_description,
            target_entity_id=a.target_entity_id,
            payload=a.payload or {},
            status=a.status,
            decision_notes=a.decision_notes,
            decided_at=a.decided_at,
            created_at=a.created_at,
        )
        for a in approvals
    ]


@router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalRequestResponse,
    summary="Get details of a specific approval request",
)
async def get_approval_details(
    approval_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalRequestResponse:
    """Retrieve specific approval request ensuring user isolation."""
    approval = await approval_workflow_agent.get_approval(db, approval_id, current_user.uid)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' not found.",
        )
    return ApprovalRequestResponse(
        id=approval.id,
        thread_id=approval.thread_id,
        action_type=approval.action_type,
        action_description=approval.action_description,
        target_entity_id=approval.target_entity_id,
        payload=approval.payload or {},
        status=approval.status,
        decision_notes=approval.decision_notes,
        decided_at=approval.decided_at,
        created_at=approval.created_at,
    )


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=dict[str, Any],
    summary="Explicitly approve a consequential action and execute it",
)
async def approve_action(
    approval_id: str,
    body: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record explicit human approval for a queued action. An LLM cannot approve itself."""
    updated = await approval_workflow_agent.decide_approval(
        db=db,
        approval_id=approval_id,
        firebase_uid=current_user.uid,
        decision="approved",
        decision_notes=body.notes,
    )

    execution_result = await approval_workflow_agent.execute_approved_action(db, updated)

    return {
        "approval_id": updated.id,
        "status": updated.status,
        "action_type": updated.action_type,
        "decided_at": updated.decided_at.isoformat() if updated.decided_at else None,
        "execution": execution_result,
    }


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=dict[str, Any],
    summary="Explicitly reject a consequential action",
)
async def reject_action(
    approval_id: str,
    body: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record explicit human rejection. The queued action will not be executed."""
    updated = await approval_workflow_agent.decide_approval(
        db=db,
        approval_id=approval_id,
        firebase_uid=current_user.uid,
        decision="rejected",
        decision_notes=body.notes,
    )

    return {
        "approval_id": updated.id,
        "status": updated.status,
        "action_type": updated.action_type,
        "decided_at": updated.decided_at.isoformat() if updated.decided_at else None,
        "notes": updated.decision_notes,
    }
