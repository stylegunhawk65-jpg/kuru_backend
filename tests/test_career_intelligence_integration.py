"""Comprehensive Unit and Integration Tests for Phase 10: Career Intelligence Integration.

Tests cover:
1. Evidence-Backed Job Matching:
   - Differentiating practically demonstrated skills, repository-supported skills, and unverified skills.
   - Arithmetic and evidence-backed match reasons.
2. Skill Gap Analysis & Gap Types:
   - demonstrated_need (failed practical assessment / unpassed challenges).
   - dependency_only (manifest presence without source implementation).
   - absent_evidence (no portfolio records).
   - Priority scoring with urgency adjustment and explainable reasons.
3. Deterministic Readiness Scoring & Similarity Neutrality:
   - verified_readiness_score and readiness_breakdown.
   - Strict similarity neutrality guarantee (SkillProof similarity never equates to competency or AI use).
4. Career Planning with Assessment Weak-Point Insights:
   - Injecting practical assessment test insights into learning roadmaps.
   - Weekly hour adaptation and what-if readiness projection notice.
5. Authentic Learning Resources:
   - Zero hallucinated URLs; strict official domain whitelist enforcement.
6. Project Recommendations Validated Against Target Job:
   - Matching tech_stack to job requirements, populating validated_job_technologies and job_alignment_summary.
7. What-If Simulation & Projections:
   - Projected fit gains, unlocked jobs, and explicit hiring disclaimer.
8. Multi-Tenant Cross-User Isolation & Security:
   - Verification that user data, assessments, and intelligence reports cannot be accessed cross-tenant.
   - Unauthenticated request rejection.
"""

from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import PracticalAssessment
from app.models.job import JobPosting
from app.models.profile import StudentProfile
from app.models.skill import SkillGraphEdge, StudentSkill
from app.models.skillproof import SkillProofEvidence, SkillProofRun
from app.schemas.agents import (
    CareerPlanResult,
    MatchedJobItem,
    PrioritizedSkillGapItem,
    ProjectRecommendationItem,
)
from app.services.agents.career_planning_agent import career_planning_agent
from app.services.agents.github_agent import github_analysis_agent
from app.services.agents.job_matching_agent import job_matching_agent
from app.services.agents.project_recommendation_agent import project_recommendation_agent
from app.services.agents.resource_registry import is_url_genuine
from app.services.agents.resource_research_agent import resource_research_agent
from app.services.agents.skill_gap_agent import skill_gap_agent
from app.services.career_intelligence import career_intelligence_service
from app.services.llm.career_tasks import career_task_service
from app.services.llm.mock_provider import MockLLMProvider
from app.services.matcher import calculate_job_match, normalize_skill


# -----------------------------------------------------------------------------
# Auth Mocking & Test Constants
# -----------------------------------------------------------------------------

USER_ALPHA_UID = "usr_phase10_alpha"
USER_BRAVO_UID = "usr_phase10_bravo"

USER_ALPHA_HEADERS = {"Authorization": "Bearer token_phase10_alpha"}
USER_BRAVO_HEADERS = {"Authorization": "Bearer token_phase10_bravo"}


def mock_verify_id_token(token: str, *args, **kwargs):
    if token == "token_phase10_alpha":
        return {
            "uid": USER_ALPHA_UID,
            "email": "alpha_phase10@kuru.ai",
            "name": "Alpha Phase 10 Candidate",
        }
    elif token == "token_phase10_bravo":
        return {
            "uid": USER_BRAVO_UID,
            "email": "bravo_phase10@kuru.ai",
            "name": "Bravo Phase 10 Candidate",
        }
    raise ValueError("Invalid test token")


@pytest.fixture(autouse=True)
def patch_firebase_auth():
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_id_token):
        yield


@pytest.fixture
def mock_llm_provider() -> MockLLMProvider:
    return MockLLMProvider()


# -----------------------------------------------------------------------------
# Database Seed Fixture
# -----------------------------------------------------------------------------

@pytest.fixture
async def seed_phase10_data(db_session: AsyncSession):
    """Seed comprehensive candidate profiles, skills, assessments, and jobs."""
    now = datetime.now(timezone.utc)

    # 1. Student Profile for User Alpha
    profile_alpha = StudentProfile(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        email="alpha_phase10@kuru.ai",
        full_name="Alpha Candidate",
        target_roles=["Backend Engineer", "Distributed Systems Engineer"],
        interests=["Distributed Systems", "API Design", "Performance"],
        preferred_locations=["Bengaluru", "Remote"],
    )
    db_session.add(profile_alpha)

    # 2. Student Skills for User Alpha
    # Python: repository_supported
    skill_py = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        skill_name="Python",
        category="Language",
        confidence_score=0.95,
        verification_status="repository_supported",
        evidence=[{"type": "ast_definition", "file": "src/api.py", "lines": [10, 45]}],
        source_repositories=["kuru-backend"],
    )
    # FastAPI: repository_supported
    skill_fastapi = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        skill_name="FastAPI",
        category="Framework",
        confidence_score=0.90,
        verification_status="repository_supported",
        evidence=[{"type": "ast_import", "file": "src/main.py", "lines": [1, 5]}],
        source_repositories=["kuru-backend"],
    )
    # Docker: practically_demonstrated (via passed practical assessment)
    skill_docker = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        skill_name="Docker",
        category="DevOps/Tool",
        confidence_score=0.88,
        verification_status="practically_demonstrated",
        evidence=[{"type": "practical_assessment", "score": 96.0}],
        source_repositories=["kuru-backend"],
    )
    db_session.add_all([skill_py, skill_fastapi, skill_docker])

    # 3. Practical Assessment Records
    # Docker: passed challenge (demonstrated competency)
    pa_docker = PracticalAssessment(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        skill_name="Docker",
        assessment_level="intermediate",
        challenge_type="debugging",
        status="passed",
        passed=True,
        score=96.0,
        challenge_data={"title": "Multi-stage Dockerfile Optimization"},
    )
    # Redis: failed practical challenge (demonstrates active learning need)
    pa_redis = PracticalAssessment(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        skill_name="Redis",
        assessment_level="intermediate",
        challenge_type="coding",
        status="failed",
        passed=False,
        score=40.0,
        challenge_data={"title": "Distributed Rate Limiter"},
    )
    db_session.add_all([pa_docker, pa_redis])

    # 4. SkillProof Evidence Records (Phase 8)
    # PostgreSQL: manifest-only evidence (dependency without full implementation)
    run_1 = SkillProofRun(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        repository_id="repo-alpha-1",
        repository_full_name="candidate/kuru-backend",
        target_skills=["PostgreSQL"],
        status="completed",
        summary={},
        honest_reporting={},
    )
    db_session.add(run_1)

    sp_postgres = SkillProofEvidence(
        id=str(uuid.uuid4()),
        run_id=run_1.id,
        firebase_uid=USER_ALPHA_UID,
        file_path="requirements.txt",
        language="Text",
        has_implementation=False,
        has_dependency=True,
        skills_detected=[
            {"skill": "PostgreSQL", "has_dependency": True, "has_implementation": False}
        ],
        similarity_findings=[],
    )
    db_session.add(sp_postgres)

    # 5. Graph Edges
    edge = SkillGraphEdge(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALPHA_UID,
        source_skill="FastAPI",
        target_skill="Python",
        relationship_type="requires_language",
        weight=1.0,
    )
    db_session.add(edge)

    # 6. Realistic Job Postings
    job_1 = JobPosting(
        id=str(uuid.uuid4()),
        source="curated_india",
        source_id="job_backend_razorpay",
        dedup_hash="hash_razorpay_backend",
        title="Senior Backend Engineer",
        company="Razorpay",
        location="Bengaluru",
        is_remote=False,
        job_type="full_time",
        description="Build payment microservices in Python, FastAPI, Docker, Redis, and PostgreSQL.",
        url="https://example.com/razorpay-backend",
        required_skills=["Python", "FastAPI", "Docker", "Redis", "PostgreSQL"],
        posted_at=now,
        last_seen_at=now,
        is_active=True,
    )
    job_2 = JobPosting(
        id=str(uuid.uuid4()),
        source="curated_india",
        source_id="job_platform_swiggy",
        dedup_hash="hash_swiggy_platform",
        title="Platform Engineer",
        company="Swiggy",
        location="Remote",
        is_remote=True,
        job_type="full_time",
        description="Orchestrate cloud workloads with Docker, Kubernetes, and Golang.",
        url="https://example.com/swiggy-platform",
        required_skills=["Docker", "Kubernetes", "Golang"],
        posted_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add_all([job_1, job_2])
    await db_session.commit()


# -----------------------------------------------------------------------------
# 1. Job Matching with Evidence-Backed Explanations
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_matching_evidence_backed_reasons(
    db_session: AsyncSession, seed_phase10_data
):
    """Verify job matching agent categorizes skills by verification status and produces transparent reasons."""
    matches = await job_matching_agent.run(
        db=db_session,
        firebase_uid=USER_ALPHA_UID,
        target_role="Backend Engineer",
        limit=5,
    )
    assert len(matches) >= 1
    top_match = matches[0]

    # Verify demonstrated vs repository supported skills
    assert "Docker" in top_match.demonstrated_skills
    assert "Python" in top_match.repo_supported_skills or "FastAPI" in top_match.repo_supported_skills

    # Match reasons must explain practically demonstrated skills
    assert any("Practically verified skills" in reason for reason in top_match.match_reasons)
    assert any("Repository-supported skills" in reason for reason in top_match.match_reasons)

    # Missing skills breakdown contains reasons
    assert len(top_match.missing_skills_breakdown) >= 1
    missing_skill_names = [item.get("skill_name") or item.get("skill") for item in top_match.missing_skills_breakdown]
    assert "Redis" in missing_skill_names or "PostgreSQL" in missing_skill_names


# -----------------------------------------------------------------------------
# 2. Skill Gap Analysis & Gap Types
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_skill_gap_analysis_gap_types(
    db_session: AsyncSession, seed_phase10_data
):
    """Verify skill gap agent differentiates demonstrated_need, dependency_only, and absent_evidence."""
    assessment = await career_intelligence_service.get_or_create_assessment(
        db=db_session,
        firebase_uid=USER_ALPHA_UID,
        target_role="Backend Engineer",
        force_refresh=True,
    )

    missing_map = {m["skill_name"]: m for m in assessment.missing_skills}

    # Redis was attempted and failed in PracticalAssessment -> demonstrated_need
    if "Redis" in missing_map:
        redis_gap = missing_map["Redis"]
        assert redis_gap["gap_type"] == "demonstrated_need"
        assert "practical sandbox assessment" in redis_gap["gap_reason"].lower()

    # PostgreSQL was found only in manifest -> dependency_only
    if "PostgreSQL" in missing_map:
        pg_gap = missing_map["PostgreSQL"]
        assert pg_gap["gap_type"] == "dependency_only"
        assert "dependency manifest" in pg_gap["gap_reason"].lower()

    # Prioritized gaps include gap_type and explainable reasons
    assert len(assessment.prioritized_gaps) > 0
    top_gap = assessment.prioritized_gaps[0]
    assert top_gap["gap_type"] in ["demonstrated_need", "dependency_only", "absent_evidence"]
    assert len(top_gap["reasons"]) >= 1


# -----------------------------------------------------------------------------
# 3. Deterministic Readiness Scoring & Similarity Neutrality
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_readiness_scoring_and_similarity_neutrality(
    db_session: AsyncSession, seed_phase10_data
):
    """Verify readiness scoring is arithmetic and strictly neutral to boilerplate similarity."""
    assessment = await career_intelligence_service.get_or_create_assessment(
        db=db_session,
        firebase_uid=USER_ALPHA_UID,
        target_role="Backend Engineer",
        force_refresh=True,
    )

    assert hasattr(assessment, "verified_readiness_score")
    assert 0.0 <= assessment.verified_readiness_score <= 100.0

    breakdown = assessment.readiness_breakdown
    assert breakdown is not None
    assert "Docker" in breakdown["demonstrated_skills"]
    assert len(breakdown["repo_supported_skills"]) >= 1
    assert "similarity_neutrality_guarantee" in breakdown

    # Similarity neutrality guarantee verification
    guarantee_text = breakdown["similarity_neutrality_guarantee"]
    assert "NEVER equated with competency" in guarantee_text
    assert assessment.honest_disclaimer == guarantee_text


# -----------------------------------------------------------------------------
# 4. Career Planning with Practical Assessment Insights
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_career_planning_injects_assessment_insights(
    db_session: AsyncSession, seed_phase10_data, mock_llm_provider
):
    """Verify career planning agent identifies failed challenge areas and incorporates them into the roadmap."""
    gaps = [
        PrioritizedSkillGapItem(
            skill_name="Redis",
            priority_rank=1,
            priority_score=95.0,
            market_demand_pct=80.0,
            graph_proximity="1-Hop Synergy",
            reasons=["Attempted practical challenge and scored 40%"],
            gap_type="demonstrated_need",
        )
    ]

    plan = await career_planning_agent.run(
        provider=mock_llm_provider,
        db=db_session,
        firebase_uid=USER_ALPHA_UID,
        target_role="Backend Engineer",
        prioritized_gaps=gaps,
        weekly_hours_available=16,
    )

    assert isinstance(plan, CareerPlanResult)
    assert plan.target_role == "Backend Engineer"
    assert len(plan.weekly_modules) >= 1

    # Verify what-if readiness projection notice
    assert "projection_notice" in plan.what_if_readiness
    assert "PROJECTION ONLY" in plan.what_if_readiness["projection_notice"]


# -----------------------------------------------------------------------------
# 5. Authentic Learning Resources
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authentic_resources_no_hallucinations():
    """Verify resource research agent returns strictly verified URLs from official whitelisted domains."""
    resources_map = await resource_research_agent.run(
        skills=["Python", "FastAPI", "Docker", "Redis"],
        limit_per_skill=2,
    )

    for skill, items in resources_map.items():
        assert len(items) >= 1
        for item in items:
            assert item.is_verified is True
            assert is_url_genuine(item.url) is True
            assert "official" in item.verification_source


# -----------------------------------------------------------------------------
# 6. Project Recommendations Validated Against Target Job Requirements
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_recommendations_validated_against_job(
    mock_llm_provider,
):
    """Verify recommended projects cross-check tech stack against target job requirements."""
    job_required_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]

    projects = await project_recommendation_agent.run(
        provider=mock_llm_provider,
        target_role="Backend Engineer",
        skill_gaps=["Redis", "PostgreSQL"],
        verified_skills=["Python", "FastAPI", "Docker"],
        matched_job_titles=["Senior Backend Engineer at Razorpay"],
        selected_job_required_skills=job_required_skills,
    )

    assert len(projects) >= 1
    first_project = projects[0]
    assert isinstance(first_project, ProjectRecommendationItem)
    # Validated job technologies must be non-empty when tech_stack overlaps with job requirements
    assert len(first_project.validated_job_technologies) >= 1
    assert first_project.job_alignment_summary is not None
    assert "required technologies" in first_project.job_alignment_summary


# -----------------------------------------------------------------------------
# 7. What-If Simulation Endpoint with Explicit Hiring Disclaimer
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_what_if_simulation_endpoint_and_disclaimer(
    async_client: AsyncClient, seed_phase10_data
):
    """Verify POST /api/v1/intelligence/what-if endpoint returns projection disclaimer and score delta."""
    payload = {
        "hypothetical_skills": ["Redis", "PostgreSQL"],
        "target_role": "Backend Engineer",
    }
    response = await async_client.post(
        "/api/v1/intelligence/what-if",
        json=payload,
        headers=USER_ALPHA_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["target_role"] == "Backend Engineer"
    assert data["simulated_fit_score"] >= data["baseline_fit_score"]
    assert "Redis" in data["simulated_skills"] or "PostgreSQL" in data["simulated_skills"]
    assert "PROJECTION ONLY (NOT A HIRING GUARANTEE)" in data["disclaimer"]
    assert "0.85 proficiency confidence" in data["assumptions"]


# -----------------------------------------------------------------------------
# 8. Cross-User Isolation & Security Authorization Gates
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_intelligence_cross_user_isolation(
    async_client: AsyncClient, seed_phase10_data
):
    """Verify User Bravo cannot access or tamper with User Alpha's intelligence data."""
    # User Bravo has no seeded profile or skills
    res_b = await async_client.get(
        "/api/v1/intelligence/skill-gaps",
        headers=USER_BRAVO_HEADERS,
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["firebase_uid"] == USER_BRAVO_UID
    # User Bravo does not see User Alpha's skills
    matched_names_b = [m["skill_name"] for m in data_b["matched_skills"]]
    assert len(matched_names_b) == 0

    # Unauthenticated request rejected
    res_unauth = await async_client.get("/api/v1/intelligence/skill-gaps")
    assert res_unauth.status_code == 401
