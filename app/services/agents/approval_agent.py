"""Approval Workflow Agent — Queues and gates consequential actions for explicit human approval."""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.agent_workflow import AgentApprovalRequest

logger = logging.getLogger("kuru.agents.approval")


class ConsequentialActionError(AppException):
    """Raised when an unauthorized or unapproved consequential action is attempted."""

    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=403, error_code="CONSEQUENTIAL_ACTION_DENIED")



class ApprovalWorkflowAgent:
    """Agent that enforces human-in-the-loop authorization gates for all high-stakes actions."""

    name = "approval_workflow_agent"

    @classmethod
    async def queue_approval_request(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        thread_id: str,
        action_type: str,
        action_description: str,
        payload: dict[str, Any],
        target_entity_id: str | None = None,
    ) -> AgentApprovalRequest:
        """Create and persist a pending approval request in PostgreSQL. Never auto-approve."""
        logger.info(
            "ApprovalWorkflowAgent queueing approval for user '%s', action='%s'...",
            firebase_uid,
            action_type,
        )

        approval = AgentApprovalRequest(
            id=str(uuid.uuid4()),
            firebase_uid=firebase_uid,
            thread_id=thread_id,
            action_type=action_type,
            action_description=action_description,
            target_entity_id=target_entity_id,
            payload=payload,
            status="pending",
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return approval

    @classmethod
    async def get_approval(
        cls,
        db: AsyncSession,
        approval_id: str,
        firebase_uid: str,
    ) -> AgentApprovalRequest | None:
        """Fetch a specific approval request strictly isolated to the requesting user."""
        stmt = (
            select(AgentApprovalRequest)
            .where(AgentApprovalRequest.id == approval_id)
            .where(AgentApprovalRequest.firebase_uid == firebase_uid)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def list_user_approvals(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        status_filter: str | None = None,
    ) -> list[AgentApprovalRequest]:
        """List all approval requests for the authenticated student."""
        stmt = (
            select(AgentApprovalRequest)
            .where(AgentApprovalRequest.firebase_uid == firebase_uid)
            .order_by(AgentApprovalRequest.created_at.desc())
        )
        if status_filter:
            stmt = stmt.where(AgentApprovalRequest.status == status_filter)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def decide_approval(
        cls,
        db: AsyncSession,
        approval_id: str,
        firebase_uid: str,
        decision: str,  # "approved" or "rejected"
        decision_notes: str | None = None,
    ) -> AgentApprovalRequest:
        """Record explicit human decision on a queued request. Strictly user-isolated."""
        logger.info(
            "User '%s' recording decision '%s' on approval '%s'",
            firebase_uid,
            decision,
            approval_id,
        )

        approval = await cls.get_approval(db, approval_id, firebase_uid)
        if not approval:
            raise AppException(
                detail=f"Approval request '{approval_id}' not found or unauthorized.",
                status_code=404,
                error_code="APPROVAL_NOT_FOUND",
            )

        if approval.status != "pending":
            raise AppException(
                detail=f"Approval request '{approval_id}' is already finalized (status='{approval.status}').",
                status_code=400,
                error_code="APPROVAL_ALREADY_DECIDED",
            )

        if decision not in {"approved", "rejected"}:
            raise AppException(
                detail=f"Invalid decision '{decision}'. Must be 'approved' or 'rejected'.",
                status_code=422,
                error_code="INVALID_APPROVAL_DECISION",
            )

        approval.status = decision
        approval.decision_notes = decision_notes
        approval.decided_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(approval)
        return approval

    @classmethod
    async def execute_approved_action(
        cls,
        db: AsyncSession,
        approval: AgentApprovalRequest,
    ) -> dict[str, Any]:
        """Execute the consequential action once explicitly verified as approved."""
        if approval.status != "approved":
            raise ConsequentialActionError(
                f"Cannot execute unapproved action '{approval.action_type}' (status='{approval.status}')."
            )

        logger.info("Executing approved action '%s' for '%s'...", approval.action_type, approval.firebase_uid)

        execution_result: dict[str, Any] = {
            "action_type": approval.action_type,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        }

        if approval.action_type == "job_application":
            execution_result["message"] = (
                f"Application package prepared and approved for job '{approval.target_entity_id}'."
            )
        elif approval.action_type == "resume_export":
            execution_result["message"] = "Tailored resume bundle generated for export."
        else:
            execution_result["message"] = f"Action '{approval.action_type}' executed successfully."

        approval.status = "executed"
        await db.commit()
        return execution_result


approval_workflow_agent = ApprovalWorkflowAgent()
