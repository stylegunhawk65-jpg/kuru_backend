"""Comprehensive Unit & Integration Tests for Phase 7 Multi-Agent System.

Tests cover:
1. Authentic Resource Registry & Zero Hallucinated URL validation
2. LangChain Tools (official resource lookup, URL verification)
3. 9 Logical Agents (Profile, GitHub, Jobs, Gaps, Plan, Resources, Projects, Resume, Approval)
4. LangGraph Multi-Agent Orchestrator (Full 9-agent pipeline, Roadmap sub-workflow)
5. Human-in-the-loop Approval Workflow & State Persistence
6. Per-User Isolation & Security Authorization Gates
"""

from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_workflow import AgentApprovalRequest, AgentWorkflowRun
from app.models.job import JobPosting
from app.models.profile import StudentProfile
from app.models.skill import SkillGraphEdge, StudentSkill
from app.schemas.agents import (
    CareerPlanResult,
    CareerTwinAgentState,
    ConsolidatedProfile,
    MatchedJobItem,
    PrioritizedSkillGapItem,
    ProjectRecommendationItem,
    TailoredResumeResult,
    VerifiedSkillItem,
)
from app.services.agents.approval_agent import ApprovalWorkflowAgent, approval_workflow_agent
from app.services.agents.career_planning_agent import CareerPlanningAgent, career_planning_agent
from app.services.agents.github_agent import GitHubAnalysisAgent, github_analysis_agent
from app.services.agents.job_matching_agent import JobMatchingAgent, job_matching_agent
from app.services.agents.profile_agent import CareerProfileAgent, career_profile_agent
from app.services.agents.project_recommendation_agent import (
    ProjectRecommendationAgent,
    project_recommendation_agent,
)
from app.services.agents.resource_registry import (
    ALLOWED_OFFICIAL_DOMAINS,
    get_curated_learning_resources,
    is_url_genuine,
)
from app.services.agents.resource_research_agent import (
    ResourceResearchAgent,
    resource_research_agent,
)
from app.services.agents.resume_agent import ResumeAgent, resume_agent
from app.services.agents.skill_gap_agent import SkillGapAgent, skill_gap_agent
from app.services.agents.tools import (
    lookup_official_learning_resources,
    verify_resource_url,
)
from app.services.agents.workflow import CareerTwinWorkflowService, workflow_service
from app.services.llm.mock_provider import MockLLMProvider


# ---------------------------------------------------------------------------
# Test Fixtures & Firebase Auth Mocking
# ---------------------------------------------------------------------------

def mock_verify_token(token: str, *args, **kwargs):
    if token == "token_user_a":
        return {
            "uid": "usr_agent_alpha_123",
            "email": "alpha_student@example.com",
            "name": "Alpha Agent Student",
        }
    elif token == "token_user_b":
        return {
            "uid": "usr_agent_bravo_456",
            "email": "bravo_student@example.com",
            "name": "Bravo Agent Student",
        }
    raise ValueError("Unrecognized test token")


@pytest.fixture(autouse=True)
def patch_firebase_auth():
    """Automatically mock token verification for multi-agent tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}
USER_A_UID = "usr_agent_alpha_123"
USER_B_UID = "usr_agent_bravo_456"


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
async def setup_agent_student_data(db_session: AsyncSession):
    """Populate test DB with profile, skills, graph edges, and job postings."""
    now = datetime.now(timezone.utc)

    # 1. User A Profile
    profile_a = StudentProfile(
        id=str(uuid.uuid4()),
        firebase_uid=USER_A_UID,
        email="alpha_student@example.com",
        full_name="Alpha Agent Student",
        target_roles=["Backend Engineer", "Cloud Developer"],
        interests=["Distributed Systems", "APIs"],
        education=[{"degree": "B.Tech Computer Science", "graduation_year": 2025}],
        preferred_locations=["Bengaluru", "Remote"],
    )
    db_session.add(profile_a)

    # 2. User A Skills
    skill_py = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_A_UID,
        skill_name="Python",
        category="Language",
        confidence_score=0.92,
        evidence=[{"type": "repo", "name": "repo_alpha"}],
        source_repositories=["repo_alpha"],
    )
    skill_fastapi = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_A_UID,
        skill_name="FastAPI",
        category="Framework",
        confidence_score=0.88,
        evidence=[{"type": "repo", "name": "repo_alpha"}],
        source_repositories=["repo_alpha"],
    )
    db_session.add_all([skill_py, skill_fastapi])

    # 3. Skill Graph Edges (Python -> FastAPI, FastAPI -> Docker)
    edge_1 = SkillGraphEdge(
        id=str(uuid.uuid4()),
        firebase_uid=USER_A_UID,
        source_skill="Python",
        target_skill="FastAPI",
        relationship_type="framework_of",
        weight=0.9,
    )
    edge_2 = SkillGraphEdge(
        id=str(uuid.uuid4()),
        firebase_uid=USER_A_UID,
        source_skill="FastAPI",
        target_skill="Docker",
        relationship_type="commonly_used_with",
        weight=0.8,
    )
    db_session.add_all([edge_1, edge_2])


    # 4. Job Postings
    job_1 = JobPosting(
        id="job_agent_test_1",
        source="curated_india",
        source_id="job_backend_in_1",
        dedup_hash="hash_agt_1",
        title="Junior Backend Engineer",
        company="Razorpay",
        location="Bengaluru, Karnataka",
        is_remote=True,
        job_type="full_time",
        description="Build backend services using Python, FastAPI, Docker, and PostgreSQL.",
        url="https://razorpay.com/jobs/junior-backend",
        required_skills=["Python", "FastAPI", "Docker", "PostgreSQL", "Redis"],
        posted_at=now,
        last_seen_at=now,
        is_active=True,
    )
    job_2 = JobPosting(
        id="job_agent_test_2",
        source="curated_india",
        source_id="job_backend_in_2",
        dedup_hash="hash_agt_2",
        title="Python API Developer Intern",
        company="Swiggy",
        location="Bengaluru, Karnataka",
        is_remote=False,
        job_type="internship",
        description="Internship for API development with Python and FastAPI.",
        url="https://swiggy.com/careers/intern-api",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        posted_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add_all([job_1, job_2])
    await db_session.commit()


# ---------------------------------------------------------------------------
# 1. Resource Registry & URL Verification Tests
# ---------------------------------------------------------------------------

def test_resource_registry_genuine_curation():
    """Verify registry returns strictly official documentation and trusted sources."""
    py_resources = get_curated_learning_resources("Python")
    assert len(py_resources) >= 2
    for r in py_resources:
        assert is_url_genuine(r.url) is True
        assert any(domain in r.url for domain in ALLOWED_OFFICIAL_DOMAINS)

    fastapi_res = get_curated_learning_resources("FastAPI")
    assert len(fastapi_res) >= 1
    assert "tiangolo.com" in fastapi_res[0].url
    assert is_url_genuine(fastapi_res[0].url) is True


def test_is_url_genuine_rejects_hallucinations():
    """Verify validator strictly rejects untrusted or invented domains."""
    # Genuine domains
    assert is_url_genuine("https://docs.python.org/3/tutorial/") is True
    assert is_url_genuine("https://fastapi.tiangolo.com/tutorial/") is True
    assert is_url_genuine("https://docs.docker.com/get-started/") is True
    assert is_url_genuine("https://developer.mozilla.org/en-US/") is True

    # Untrusted / Hallucinated / Malicious domains
    assert is_url_genuine("http://fake-learn-fastapi-quick.xyz/guide") is False
    assert is_url_genuine("https://scam-programming-degree.ru/python") is False
    assert is_url_genuine("https://not-in-allowed-list.com/course") is False
    assert is_url_genuine("invalid-url-string") is False
    assert is_url_genuine("") is False


def test_langchain_tools_execution():
    """Verify LangChain @tool wrappers execute deterministically and safely."""
    # 1. lookup_official_learning_resources
    tools_res = lookup_official_learning_resources.invoke({"skills": ["Docker"]})
    assert isinstance(tools_res, dict)
    assert "Docker" in tools_res
    assert len(tools_res["Docker"]) >= 1
    assert "docker.com" in tools_res["Docker"][0]["url"]

    # 2. verify_resource_url
    assert verify_resource_url.invoke({"url": "https://redis.io/docs/"}) is True
    assert verify_resource_url.invoke({"url": "http://bogus-tutorial-site.biz"}) is False


# ---------------------------------------------------------------------------
# 2. Unit Tests for Individual Logical Agents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_career_profile_agent(db_session: AsyncSession, setup_agent_student_data):
    """Career Profile Agent consolidates student profile, target roles, and interests."""
    profile = await career_profile_agent.run(db_session, USER_A_UID)
    assert isinstance(profile, ConsolidatedProfile)
    assert profile.firebase_uid == USER_A_UID
    assert profile.primary_target_role == "Backend Engineer"
    assert "Distributed Systems" in profile.interests

    # Overriding target role
    profile_override = await career_profile_agent.run(
        db_session, USER_A_UID, target_role_override="Machine Learning Engineer"
    )
    assert profile_override.primary_target_role == "Machine Learning Engineer"


@pytest.mark.asyncio
async def test_github_analysis_agent(db_session: AsyncSession, setup_agent_student_data):
    """GitHub Analysis Agent retrieves verified skills and 1-hop graph edges."""
    skills = await github_analysis_agent.run(db_session, USER_A_UID)
    assert len(skills) >= 2
    skill_names = {s.skill_name for s in skills}
    assert "Python" in skill_names
    assert "FastAPI" in skill_names

    py_skill = next(s for s in skills if s.skill_name == "Python")
    assert py_skill.confidence_score > 0.9
    assert py_skill.source_evidence_count >= 1
    assert "FastAPI" in py_skill.related_skills


@pytest.mark.asyncio
async def test_job_matching_agent(db_session: AsyncSession, setup_agent_student_data):
    """Job Matching Agent matches postings with deterministic score ranking."""
    matches = await job_matching_agent.run(db_session, USER_A_UID, target_role="Backend Engineer", limit=5)
    assert len(matches) >= 1
    top_match = matches[0]
    assert isinstance(top_match, MatchedJobItem)
    assert "Razorpay" in top_match.company or "Swiggy" in top_match.company
    assert top_match.match_score > 0
    assert "Python" in top_match.matching_skills


@pytest.mark.asyncio
async def test_skill_gap_agent(db_session: AsyncSession, setup_agent_student_data):
    """Skill Gap Agent identifies missing skills and computes priority and proximity."""
    gaps = await skill_gap_agent.run(db_session, USER_A_UID, target_role="Backend Engineer")
    assert len(gaps) >= 1
    gap_names = [g.skill_name for g in gaps]
    assert "Docker" in gap_names or "PostgreSQL" in gap_names or "Redis" in gap_names

    docker_gap = next((g for g in gaps if g.skill_name == "Docker"), None)
    if docker_gap:
        assert docker_gap.priority_rank >= 1


@pytest.mark.asyncio
async def test_career_planning_agent(db_session: AsyncSession, setup_agent_student_data, mock_provider):
    """Career Planning Agent synthesizes structured milestones and roadmap via shared LLM."""
    gaps = [
        PrioritizedSkillGapItem(
            skill_name="Docker",
            priority_rank=1,
            priority_score=9.5,
            market_demand_pct=85.0,
            graph_proximity="1-hop",
            reasons=["Required by top matching job"],
        )
    ]
    plan = await career_planning_agent.run(
        provider=mock_provider,
        db=db_session,
        firebase_uid=USER_A_UID,
        target_role="Backend Engineer",
        prioritized_gaps=gaps,
        weekly_hours_available=15,
    )
    assert isinstance(plan, CareerPlanResult)
    assert plan.target_role == "Backend Engineer"
    assert len(plan.weekly_modules) >= 1
    assert len(plan.learning_principles) >= 1


@pytest.mark.asyncio
async def test_resource_research_agent():
    """Resource Research Agent returns strictly validated official links without inventing URLs."""
    skills = ["FastAPI", "Docker", "Redis"]
    result = await resource_research_agent.run(skills=skills, limit_per_skill=2)
    assert "FastAPI" in result
    assert "Docker" in result
    assert "Redis" in result

    for skill, resources in result.items():
        assert len(resources) >= 1
        for res in resources:
            assert is_url_genuine(res.url) is True
            assert res.provider is not None


@pytest.mark.asyncio
async def test_project_recommendation_agent(mock_provider):
    """Project Recommendation Agent formulates portfolio projects tied to gaps."""
    projects = await project_recommendation_agent.run(
        provider=mock_provider,
        target_role="Backend Engineer",
        skill_gaps=["Docker", "PostgreSQL", "Redis"],
        verified_skills=["Python", "FastAPI"],
        matched_job_titles=["Junior Backend Engineer"],
    )
    assert len(projects) >= 1
    assert isinstance(projects[0], ProjectRecommendationItem)
    assert len(projects[0].target_skill_gaps) >= 1
    assert projects[0].difficulty_level in {"Beginner", "Intermediate", "Advanced"}


@pytest.mark.asyncio
async def test_resume_agent(mock_provider):
    """Resume Agent tailors summary and bullet points targeting role."""
    resume = await resume_agent.run(
        provider=mock_provider,
        target_role="Backend Engineer",
        bullet_points=["Built REST APIs using Python and FastAPI."],
        verified_skills=["Python", "FastAPI"],
        job_description="Seeking a Backend Engineer proficient in Python and FastAPI.",
    )
    assert isinstance(resume, TailoredResumeResult)
    assert resume.target_role == "Backend Engineer"
    assert len(resume.bullet_points) >= 1
    assert resume.alignment_explanation is not None



@pytest.mark.asyncio
async def test_approval_workflow_agent(db_session: AsyncSession):
    """Approval Workflow Agent enforces human-in-the-loop authorization gates."""
    # 1. Queue an approval request
    approval = await approval_workflow_agent.queue_approval_request(
        db=db_session,
        firebase_uid=USER_A_UID,
        thread_id="thread_test_123",
        action_type="job_application",
        action_description="Submit application to Razorpay for Junior Backend Engineer",
        payload={"job_id": "job_agent_test_1"},
        target_entity_id="job_agent_test_1",
    )
    assert approval.id is not None
    assert approval.status == "pending"

    # 2. List user approvals
    user_approvals = await approval_workflow_agent.list_user_approvals(db_session, USER_A_UID)
    assert len(user_approvals) >= 1
    assert any(a.id == approval.id for a in user_approvals)

    # 3. User B cannot see or decide User A's approval
    b_approvals = await approval_workflow_agent.list_user_approvals(db_session, USER_B_UID)
    assert not any(a.id == approval.id for a in b_approvals)

    # 4. Human approves the action
    decided = await approval_workflow_agent.decide_approval(
        db=db_session,
        approval_id=approval.id,
        firebase_uid=USER_A_UID,
        decision="approved",
        decision_notes="Looks great, proceed with application.",
    )
    assert decided.status == "approved"
    assert decided.decided_at is not None

    # 5. Execute approved action
    exec_res = await approval_workflow_agent.execute_approved_action(db_session, decided)
    assert exec_res["status"] == "success"
    assert decided.status == "executed"


# ---------------------------------------------------------------------------
# 3. LangGraph Workflow Orchestration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_full_career_twin_workflow(
    db_session: AsyncSession, setup_agent_student_data, mock_provider
):
    """Test full 9-agent LangGraph execution pipeline with database audit persistence."""
    svc = CareerTwinWorkflowService()
    run_id, final_state = await svc.run_full_workflow(
        db=db_session,
        firebase_uid=USER_A_UID,
        target_role="Backend Engineer",
        weekly_hours=14,
        action_to_queue="job_application",
        provider=mock_provider,
    )

    assert run_id is not None
    assert final_state["firebase_uid"] == USER_A_UID
    assert final_state["target_role"] == "Backend Engineer"

    # Verify state populated by agents
    assert final_state.get("profile") is not None
    assert len(final_state.get("skills", [])) >= 2
    assert len(final_state.get("matched_jobs", [])) >= 1
    assert len(final_state.get("skill_gaps", [])) >= 1
    assert final_state.get("career_plan") is not None
    assert len(final_state.get("resources", {})) >= 1
    assert len(final_state.get("projects", [])) >= 1
    assert final_state.get("resume") is not None

    # Verify Approval Gate paused the consequential action
    assert final_state["approval_status"] == "pending"
    assert final_state["pending_approval"] is not None
    assert final_state["pending_approval"]["action_type"] == "job_application"

    # Verify Audit Run persisted in DB
    audit = await db_session.get(AgentWorkflowRun, run_id)
    assert audit is not None
    assert audit.workflow_type == "full_career_twin"
    assert audit.status == "waiting_approval"
    assert audit.state_summary["target_role"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_run_full_career_twin_pipeline_bypasses_approval_gate_when_no_action(
    db_session: AsyncSession, setup_agent_student_data, mock_provider
):
    """Test full 9-agent LangGraph execution pipeline when no consequential action is requested."""
    svc = CareerTwinWorkflowService()
    run_id, final_state = await svc.run_full_workflow(
        db=db_session,
        firebase_uid=USER_A_UID,
        target_role="Backend Engineer",
        weekly_hours=14,
        action_to_queue=None,
        provider=mock_provider,
    )

    assert run_id is not None
    assert final_state["approval_status"] == "none"
    assert final_state["pending_approval"] is None
    assert any("approval_gate_node:bypassed_or_approved" in s for s in final_state["step_history"])

    # Verify Audit Run shows completed rather than waiting_approval
    audit = await db_session.get(AgentWorkflowRun, run_id)
    assert audit is not None
    assert audit.status == "completed"


@pytest.mark.asyncio
async def test_run_roadmap_subworkflow(
    db_session: AsyncSession, setup_agent_student_data, mock_provider
):
    """Test focused incremental sub-workflow: skill_gaps -> career_planning -> resources -> projects."""
    svc = CareerTwinWorkflowService()
    run_id, final_state = await svc.run_roadmap_subworkflow(
        db=db_session,
        firebase_uid=USER_A_UID,
        target_role="Backend Engineer",
        weekly_hours=10,
        provider=mock_provider,
    )

    assert run_id is not None
    assert final_state["career_plan"] is not None
    assert len(final_state["projects"]) >= 1
    assert len(final_state["resources"]) >= 1

    # Verify step history
    history = final_state.get("step_history", [])
    assert any("skill_gap_node" in s for s in history)
    assert any("career_planning_node" in s for s in history)
    assert any("resource_research_node" in s for s in history)
    assert any("project_recommendation_node" in s for s in history)


# ---------------------------------------------------------------------------
# 4. API Endpoints Integration & Authorization Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_trigger_career_twin_workflow(
    async_client: AsyncClient, db_session: AsyncSession, setup_agent_student_data
):
    """POST /api/v1/agents/workflows/career-twin executes full pipeline."""
    payload = {
        "target_role": "Backend Engineer",
        "weekly_hours_available": 12,
        "consequential_action_requested": "job_application",
    }
    response = await async_client.post(
        "/api/v1/agents/workflows/career-twin",
        json=payload,
        headers=USER_A_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["target_role"] == "Backend Engineer"
    assert data["approval_status"] == "pending"
    assert data["pending_approval"] is not None
    assert data["state_summary"]["has_roadmap"] is True
    assert data["state_summary"]["has_tailored_resume"] is True


@pytest.mark.asyncio
async def test_api_trigger_roadmap_workflow(
    async_client: AsyncClient, db_session: AsyncSession, setup_agent_student_data
):
    """POST /api/v1/agents/workflows/roadmap executes incremental roadmap pipeline."""
    payload = {
        "target_role": "Backend Engineer",
        "weekly_hours_available": 15,
    }
    response = await async_client.post(
        "/api/v1/agents/workflows/roadmap",
        json=payload,
        headers=USER_A_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["career_plan"] is not None
    assert len(data["recommended_projects"]) >= 1
    assert len(data["genuine_resources"]) >= 1


@pytest.mark.asyncio
async def test_api_workflow_audit_get(
    async_client: AsyncClient, db_session: AsyncSession, setup_agent_student_data
):
    """GET /api/v1/agents/workflows/{run_id} retrieves audit record with per-user isolation."""
    # 1. Trigger workflow
    trigger_res = await async_client.post(
        "/api/v1/agents/workflows/roadmap",
        json={"target_role": "Backend Engineer"},
        headers=USER_A_HEADERS,
    )
    run_id = trigger_res.json()["run_id"]

    # 2. User A retrieves their run
    get_res = await async_client.get(
        f"/api/v1/agents/workflows/{run_id}",
        headers=USER_A_HEADERS,
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == run_id

    # 3. User B cannot access User A's run
    forbidden_res = await async_client.get(
        f"/api/v1/agents/workflows/{run_id}",
        headers=USER_B_HEADERS,
    )
    assert forbidden_res.status_code == 404


@pytest.mark.asyncio
async def test_api_approvals_lifecycle_and_isolation(
    async_client: AsyncClient, db_session: AsyncSession, setup_agent_student_data
):
    """Test approval listing, human approval decision, rejection, and isolation."""
    # 1. Trigger full workflow to generate pending approval
    trigger_res = await async_client.post(
        "/api/v1/agents/workflows/career-twin",
        json={
            "target_role": "Backend Engineer",
            "consequential_action_requested": "job_application",
        },
        headers=USER_A_HEADERS,
    )
    approval_id = trigger_res.json()["pending_approval"]["id"]

    # 2. List pending approvals
    list_res = await async_client.get("/api/v1/agents/approvals", headers=USER_A_HEADERS)
    assert list_res.status_code == 200
    approvals = list_res.json()
    assert any(a["id"] == approval_id for a in approvals)

    # 3. User B cannot see User A's approval in their list
    b_list_res = await async_client.get("/api/v1/agents/approvals", headers=USER_B_HEADERS)
    assert not any(a["id"] == approval_id for a in b_list_res.json())

    # 4. User B cannot approve User A's request
    b_approve_res = await async_client.post(
        f"/api/v1/agents/approvals/{approval_id}/approve",
        json={"notes": "Malicious approval attempt"},
        headers=USER_B_HEADERS,
    )
    assert b_approve_res.status_code == 404

    # 5. User A approves the request
    a_approve_res = await async_client.post(
        f"/api/v1/agents/approvals/{approval_id}/approve",
        json={"notes": "Authorized by student."},
        headers=USER_A_HEADERS,
    )
    assert a_approve_res.status_code == 200
    res_data = a_approve_res.json()
    assert res_data["status"] == "executed"
    assert res_data["execution"]["status"] == "success"


    # 6. Cannot decide on an already approved request
    duplicate_res = await async_client.post(
        f"/api/v1/agents/approvals/{approval_id}/approve",
        json={"notes": "Second attempt"},
        headers=USER_A_HEADERS,
    )
    assert duplicate_res.status_code == 400


@pytest.mark.asyncio
async def test_api_approvals_rejection(
    async_client: AsyncClient, db_session: AsyncSession, setup_agent_student_data
):
    """Test explicitly rejecting a queued action."""
    # 1. Queue approval directly
    approval = await approval_workflow_agent.queue_approval_request(
        db=db_session,
        firebase_uid=USER_A_UID,
        thread_id="thread_reject_test",
        action_type="resume_export",
        action_description="Export resume to external recruiter",
        payload={},
    )

    # 2. Reject action
    reject_res = await async_client.post(
        f"/api/v1/agents/approvals/{approval.id}/reject",
        json={"notes": "Changed my mind, do not export."},
        headers=USER_A_HEADERS,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    assert reject_res.json()["notes"] == "Changed my mind, do not export."


@pytest.mark.asyncio
async def test_api_unauthenticated_requests_denied(async_client: AsyncClient):
    """Unauthenticated requests to agent endpoints must return 401 Unauthorized."""
    endpoints = [
        ("POST", "/api/v1/agents/workflows/career-twin", {}),
        ("POST", "/api/v1/agents/workflows/roadmap", {}),
        ("GET", "/api/v1/agents/workflows/some-run-id", None),
        ("GET", "/api/v1/agents/approvals", None),
        ("POST", "/api/v1/agents/approvals/some-id/approve", {}),
        ("POST", "/api/v1/agents/approvals/some-id/reject", {}),
    ]

    for method, path, body in endpoints:
        if method == "POST":
            res = await async_client.post(path, json=body)
        else:
            res = await async_client.get(path)
        assert res.status_code == 401, f"Expected 401 for {method} {path}, got {res.status_code}"
