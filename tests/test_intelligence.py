"""Tests for Career Intelligence Service, Skill Gaps, Recommendations, and What-If Simulations."""

from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import CareerAssessment
from app.models.job import JobPosting
from app.models.profile import StudentProfile
from app.models.skill import SkillGraphEdge, StudentSkill
from app.services.career_intelligence import CareerIntelligenceService, career_intelligence_service


# Mock Firebase auth token helper
def mock_verify_token(token: str, *args, **kwargs):
    if token == "token_user_a":
        return {
            "uid": "usr_alpha_12345",
            "email": "student_alpha@example.com",
            "name": "Alpha Student",
        }
    elif token == "token_user_b":
        return {
            "uid": "usr_bravo_67890",
            "email": "student_bravo@example.com",
            "name": "Bravo Student",
        }
    raise ValueError("Unrecognized test token")


@pytest.fixture(autouse=True)
def patch_firebase_auth():
    """Automatically mock token verification for intelligence tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}


@pytest.fixture
def sample_jobs() -> list[JobPosting]:
    """Sample realistic job postings for testing intelligence service."""
    now = datetime.now(timezone.utc)
    return [
        JobPosting(
            id=str(uuid.uuid4()),
            source="curated_india",
            source_id="job_backend_1",
            dedup_hash="hash_b1",
            title="Junior Backend Engineer (Python / FastAPI)",
            company="FinTech Corp",
            location="Bengaluru, Karnataka",
            is_remote=False,
            job_type="full_time",
            description="Build scalable APIs using Python, FastAPI, PostgreSQL, and Docker.",
            url="https://example.com/job1",
            required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            posted_at=now,
            last_seen_at=now,
            is_active=True,
        ),
        JobPosting(
            id=str(uuid.uuid4()),
            source="curated_india",
            source_id="job_backend_2",
            dedup_hash="hash_b2",
            title="Backend Engineering Intern",
            company="Startup Labs",
            location="Remote",
            is_remote=True,
            job_type="internship",
            description="Work with Python, Django, Redis, and Git on microservices.",
            url="https://example.com/job2",
            required_skills=["Python", "Django", "Redis", "Git"],
            posted_at=now,
            last_seen_at=now,
            is_active=True,
        ),
        JobPosting(
            id=str(uuid.uuid4()),
            source="curated_india",
            source_id="job_data_1",
            dedup_hash="hash_d1",
            title="Data Scientist / ML Engineer",
            company="AI Innovations",
            location="Hyderabad, Telangana",
            is_remote=False,
            job_type="full_time",
            description="Machine learning pipelines with Python, PyTorch, Pandas, and SQL.",
            url="https://example.com/job3",
            required_skills=["Python", "PyTorch", "Pandas", "SQL"],
            posted_at=now,
            last_seen_at=now,
            is_active=True,
        ),
    ]


@pytest.fixture
def sample_user_a_profile() -> StudentProfile:
    """Sample profile for User A."""
    return StudentProfile(
        id=str(uuid.uuid4()),
        firebase_uid="usr_alpha_12345",
        full_name="Alpha Developer",
        target_roles=["Backend Engineer", "Software Engineer"],
        preferred_locations=["Bengaluru", "Remote"],
        interests=["Distributed Systems", "Cloud Computing"],
    )


@pytest.fixture
def sample_user_a_skills() -> list[StudentSkill]:
    """Sample skills extracted from User A's repositories."""
    return [
        StudentSkill(
            id=str(uuid.uuid4()),
            firebase_uid="usr_alpha_12345",
            skill_name="Python",
            category="Language",
            confidence_score=0.95,
            evidence=[{"type": "ast_import", "source": "main.py"}],
            source_repositories=["kuru_backend"],
        ),
        StudentSkill(
            id=str(uuid.uuid4()),
            firebase_uid="usr_alpha_12345",
            skill_name="FastAPI",
            category="Framework",
            confidence_score=0.90,
            evidence=[{"type": "manifest", "source": "pyproject.toml"}],
            source_repositories=["kuru_backend"],
        ),
        StudentSkill(
            id=str(uuid.uuid4()),
            firebase_uid="usr_alpha_12345",
            skill_name="PostgreSQL",
            category="Database",
            confidence_score=0.80,
            evidence=[{"type": "manifest", "source": "pyproject.toml"}],
            source_repositories=["kuru_backend"],
        ),
    ]


@pytest.fixture
def sample_user_a_edges() -> list[SkillGraphEdge]:
    """Sample knowledge graph edges for User A."""
    return [
        SkillGraphEdge(
            id=str(uuid.uuid4()),
            firebase_uid="usr_alpha_12345",
            source_skill="FastAPI",
            target_skill="Python",
            relationship_type="requires_language",
            weight=1.0,
        ),
        SkillGraphEdge(
            id=str(uuid.uuid4()),
            firebase_uid="usr_alpha_12345",
            source_skill="Docker",
            target_skill="Kubernetes",
            relationship_type="tooling_for",
            weight=0.9,
        ),
    ]


def test_analyze_skill_gaps_scoring_and_prioritization(
    sample_user_a_profile,
    sample_user_a_skills,
    sample_user_a_edges,
    sample_jobs,
):
    """Test skill-gap analysis, demand calculation, graph proximity, and prioritization ranking."""
    service = CareerIntelligenceService()

    result = service.analyze_skill_gaps(
        profile=sample_user_a_profile,
        skills=sample_user_a_skills,
        edges=sample_user_a_edges,
        jobs=sample_jobs,
        target_role="Backend Engineer",
    )

    # 1. Verification of fit score & readiness level
    assert 0.0 <= result["overall_fit_score"] <= 100.0
    assert result["readiness_level"] in ["Ready", "High", "Moderate", "Developing", "Early"]
    assert result["assessed_jobs_count"] >= 2  # Backend jobs selected

    # 2. Matched skills check
    matched_names = [m.skill_name for m in result["matched_skills"]]
    assert "Python" in matched_names
    assert "FastAPI" in matched_names
    assert "PostgreSQL" in matched_names

    # 3. Missing skills identified
    missing_names = [m.skill_name for m in result["missing_skills"]]
    assert "Docker" in missing_names
    assert "Git" in missing_names or "Django" in missing_names

    # 4. Prioritized gaps check
    prioritized = result["prioritized_gaps"]
    assert len(prioritized) > 0
    # First item should have priority rank 1
    assert prioritized[0].priority_rank == 1
    assert prioritized[0].priority_score >= prioritized[-1].priority_score

    # Check that reasons are informative and explainable
    for gap in prioritized:
        assert len(gap.reasons) > 0
        assert "Required by" in gap.reasons[0]

    # 5. Recommendations check
    recs = result["recommendations"]
    assert len(recs) > 0
    for rec in recs:
        assert rec.unlocked_jobs_count >= 0
        assert rec.effort_estimate in ["Low (1-2 weeks)", "Medium (3-4 weeks)", "High (5-8 weeks)"]
        assert "Mastering" in rec.reason


def test_analyze_skill_gaps_empty_profile_and_skills(sample_jobs):
    """Test that empty profile, skills, and edges do not crash and produce safe baseline assessment."""
    service = CareerIntelligenceService()

    result = service.analyze_skill_gaps(
        profile=None,
        skills=[],
        edges=[],
        jobs=sample_jobs,
        target_role="overall",
    )

    assert result["overall_fit_score"] >= 0.0
    assert result["readiness_level"] in ["Developing", "Early"]
    assert len(result["matched_skills"]) == 0
    assert len(result["missing_skills"]) > 0
    assert len(result["prioritized_gaps"]) > 0


def test_career_path_comparison(
    sample_user_a_profile,
    sample_user_a_skills,
    sample_user_a_edges,
    sample_jobs,
):
    """Test deterministic career-path comparison between Backend and Data Science."""
    service = CareerIntelligenceService()

    compare_res = service.compare_career_paths(
        profile=sample_user_a_profile,
        skills=sample_user_a_skills,
        edges=sample_user_a_edges,
        jobs=sample_jobs,
        roles=["Backend Engineer", "Data Scientist"],
    )

    assert len(compare_res.compared_roles) == 2
    backend_role = next(r for r in compare_res.compared_roles if "Backend" in r.role_name)
    data_role = next(r for r in compare_res.compared_roles if "Data" in r.role_name)

    # User A knows Python, FastAPI, PostgreSQL so Backend readiness must be higher than Data Scientist
    assert backend_role.readiness_score > data_role.readiness_score
    assert compare_res.recommended_role == backend_role.role_name
    assert "strongest career path" in compare_res.recommendation_reason
    assert "assumes 10-15 hours/week" in backend_role.assumptions


def test_what_if_simulation(
    sample_user_a_profile,
    sample_user_a_skills,
    sample_user_a_edges,
    sample_jobs,
):
    """Test simulating addition of Docker and Redis to student skills."""
    service = CareerIntelligenceService()

    sim_res = service.simulate_what_if(
        profile=sample_user_a_profile,
        skills=sample_user_a_skills,
        edges=sample_user_a_edges,
        jobs=sample_jobs,
        hypothetical_skills=["Docker", "Redis"],
        target_role="Backend Engineer",
    )

    # Simulated score must be greater than baseline score
    assert sim_res.simulated_fit_score >= sim_res.baseline_fit_score
    assert sim_res.score_delta >= 0.0
    assert "Docker" in sim_res.simulated_skills or "Redis" in sim_res.simulated_skills
    assert "0.85 proficiency confidence" in sim_res.assumptions


@pytest.mark.asyncio
async def test_intelligence_endpoints_unauthorized(async_client: AsyncClient):
    """Test intelligence endpoints reject unauthenticated requests with 401."""
    res = await async_client.get("/api/v1/intelligence/skill-gaps")
    assert res.status_code == 401

    res = await async_client.get("/api/v1/intelligence/recommendations")
    assert res.status_code == 401

    res = await async_client.post("/api/v1/intelligence/career-paths/compare", json={"roles": ["A", "B"]})
    assert res.status_code == 401

    res = await async_client.post("/api/v1/intelligence/what-if", json={"hypothetical_skills": ["Docker"]})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_skill_gap_report_lifecycle_and_persistence(async_client: AsyncClient, db_session: AsyncSession):
    """Test GET /skill-gaps, persistence in DB, and POST /skill-gaps/refresh."""
    # 1. User A requests skill gap report
    res = await async_client.get(
        "/api/v1/intelligence/skill-gaps?target_role=overall",
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["firebase_uid"] == "usr_alpha_12345"
    assert "overall_fit_score" in data
    assert "readiness_level" in data
    assert "prioritized_gaps" in data
    assert "recommendations" in data

    # 2. Check persistence in PostgreSQL/SQLite table
    stmt = select(CareerAssessment).where(
        CareerAssessment.firebase_uid == "usr_alpha_12345",
        CareerAssessment.target_role == "overall",
    )
    db_rec = (await db_session.execute(stmt)).scalar_one_or_none()
    assert db_rec is not None
    assert db_rec.overall_fit_score == data["overall_fit_score"]

    # 3. Test refresh endpoint
    refresh_res = await async_client.post(
        "/api/v1/intelligence/skill-gaps/refresh?target_role=overall",
        headers=USER_A_HEADERS,
    )
    assert refresh_res.status_code == 200
    refreshed_data = refresh_res.json()
    assert refreshed_data["firebase_uid"] == "usr_alpha_12345"


@pytest.mark.asyncio
async def test_recommendations_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/intelligence/recommendations endpoint."""
    res = await async_client.get(
        "/api/v1/intelligence/recommendations",
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 200
    recs = res.json()
    assert isinstance(recs, list)
    if recs:
        assert "skill_name" in recs[0]
        assert "unlocked_jobs_count" in recs[0]
        assert "effort_estimate" in recs[0]
        assert "reason" in recs[0]


@pytest.mark.asyncio
async def test_compare_career_paths_endpoint_and_validation(async_client: AsyncClient):
    """Test POST /api/v1/intelligence/career-paths/compare with valid payload and validation errors."""
    # Valid payload
    payload = {"roles": ["Backend Developer", "DevOps Engineer"]}
    res = await async_client.post(
        "/api/v1/intelligence/career-paths/compare",
        json=payload,
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["compared_roles"]) == 2
    assert "recommended_role" in data
    assert "recommendation_reason" in data

    # Validation failure: less than 2 roles
    bad_payload = {"roles": ["OnlyOneRole"]}
    bad_res = await async_client.post(
        "/api/v1/intelligence/career-paths/compare",
        json=bad_payload,
        headers=USER_A_HEADERS,
    )
    assert bad_res.status_code == 422


@pytest.mark.asyncio
async def test_what_if_simulation_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/intelligence/what-if endpoint."""
    payload = {
        "hypothetical_skills": ["Docker", "Kubernetes", "Redis"],
        "target_role": "Backend Developer",
    }
    res = await async_client.post(
        "/api/v1/intelligence/what-if",
        json=payload,
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_role"] == "Backend Developer"
    assert "baseline_fit_score" in data
    assert "simulated_fit_score" in data
    assert "score_delta" in data
    assert "newly_unlocked_jobs_count" in data
    assert "assumptions" in data


@pytest.mark.asyncio
async def test_career_intelligence_user_isolation(async_client: AsyncClient, db_session: AsyncSession):
    """Test that User B cannot see User A's persisted assessments and has their own isolated reports."""
    # User A creates assessment
    await async_client.get(
        "/api/v1/intelligence/skill-gaps?target_role=overall",
        headers=USER_A_HEADERS,
    )

    # User B requests their own assessment
    res_b = await async_client.get(
        "/api/v1/intelligence/skill-gaps?target_role=overall",
        headers=USER_B_HEADERS,
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["firebase_uid"] == "usr_bravo_67890"
    assert data_b["firebase_uid"] != "usr_alpha_12345"

    # Verify both records exist independently in DB
    stmt_a = select(CareerAssessment).where(CareerAssessment.firebase_uid == "usr_alpha_12345")
    rec_a = (await db_session.execute(stmt_a)).scalar_one_or_none()
    assert rec_a is not None

    stmt_b = select(CareerAssessment).where(CareerAssessment.firebase_uid == "usr_bravo_67890")
    rec_b = (await db_session.execute(stmt_b)).scalar_one_or_none()
    assert rec_b is not None

    assert rec_a.id != rec_b.id
