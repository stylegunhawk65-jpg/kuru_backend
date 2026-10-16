"""Tests for frontend-backend integration endpoints: Growth, Career Twin, Resume Tailoring, and Profile Sync."""

from unittest.mock import patch
import pytest
from httpx import AsyncClient


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
    """Automatically mock token verification."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}


@pytest.mark.asyncio
async def test_career_twin_assessment_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/career-twin returns structured CareerAssessmentModel payload."""
    res = await async_client.get("/api/v1/career-twin", headers=USER_A_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "readiness_score" in data
    assert isinstance(data["readiness_score"], int)
    assert data["readiness_score"] >= 0
    assert "demonstrated_skills_count" in data
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0
    assert "skills" in data
    assert isinstance(data["skills"], list)
    assert "connected_repositories" in data


@pytest.mark.asyncio
async def test_career_twin_reassessment_trigger(async_client: AsyncClient):
    """Test POST /api/v1/career-twin/assess forces refresh."""
    res = await async_client.post("/api/v1/career-twin/assess", headers=USER_A_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "readiness_score" in data
    assert data["readiness_score"] >= 0


@pytest.mark.asyncio
async def test_growth_goals_lifecycle(async_client: AsyncClient):
    """Test GET /api/v1/growth/goals and PATCH completion status."""
    res = await async_client.get("/api/v1/growth/goals", headers=USER_A_HEADERS)
    assert res.status_code == 200
    goals = res.json()
    assert isinstance(goals, list)
    assert len(goals) > 0
    first_goal = goals[0]
    assert "id" in first_goal
    assert "title" in first_goal
    assert "is_completed" in first_goal
    assert "priority" in first_goal

    # Patch completion
    patch_res = await async_client.patch(
        f"/api/v1/growth/goals/{first_goal['id']}",
        json={"is_completed": True},
        headers=USER_A_HEADERS,
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["is_completed"] is True


@pytest.mark.asyncio
async def test_growth_roadmap_endpoint(async_client: AsyncClient):
    """Test GET /api/v1/growth/roadmap returns milestone roadmap."""
    res = await async_client.get("/api/v1/growth/roadmap?target_role=Software Engineer", headers=USER_A_HEADERS)
    assert res.status_code == 200
    roadmap = res.json()
    assert "target_role" in roadmap
    assert "completion_percentage" in roadmap
    assert "milestones" in roadmap
    assert isinstance(roadmap["milestones"], list)
    assert len(roadmap["milestones"]) > 0
    m1 = roadmap["milestones"][0]
    assert "id" in m1
    assert "title" in m1
    assert "status" in m1
    assert "skills" in m1


@pytest.mark.asyncio
async def test_growth_resources_and_projects(async_client: AsyncClient):
    """Test GET /api/v1/growth/resources and GET /api/v1/growth/projects."""
    res_resources = await async_client.get("/api/v1/growth/resources", headers=USER_A_HEADERS)
    assert res_resources.status_code == 200
    resources = res_resources.json()
    assert isinstance(resources, list)
    assert len(resources) > 0
    for r in resources:
        assert r["url"].startswith("http")
        assert r["is_verified"] is True

    res_projects = await async_client.get("/api/v1/growth/projects", headers=USER_A_HEADERS)
    assert res_projects.status_code == 200
    projects = res_projects.json()
    assert isinstance(projects, list)
    assert len(projects) > 0
    p1 = projects[0]
    assert "title" in p1
    assert "skills" in p1
    assert "deliverable" in p1


@pytest.mark.asyncio
async def test_resume_tailor_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/resumes/tailor generates tailored ATS resume."""
    payload = {
        "target_role": "Backend Engineer",
        "target_company": "Acme Tech",
    }
    res = await async_client.post("/api/v1/resumes/tailor", json=payload, headers=USER_A_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["target_role"] == "Backend Engineer"
    assert "tailoring_metadata" in data
    assert data["firebase_uid"] == "usr_alpha_12345"


@pytest.mark.asyncio
async def test_profile_sync_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/profiles/sync creates or updates profile idempotently."""
    sync_payload = {
        "full_name": "Priya Sharma",
        "email": "priya.sharma@example.edu",
        "degree": "B.Tech Computer Science",
        "institution": "IIT Delhi",
        "graduation_year": 2026,
        "target_roles": ["Full Stack Engineer", "Backend Developer"],
        "preferred_locations": ["Bangalore", "Remote"],
        "interests": ["Distributed Systems", "Cloud"],
        "bio": "Aspiring engineer with focus on scalable backend services.",
    }
    res = await async_client.post("/api/v1/profiles/sync", json=sync_payload, headers=USER_A_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Priya Sharma"
    assert data["firebase_uid"] == "usr_alpha_12345"
    assert len(data["education"]) > 0
    assert data["education"][0]["institution"] == "IIT Delhi"

    # Resyncing updates idempotently without 409 Conflict
    sync_payload["full_name"] = "Priya Sharma (Updated)"
    res2 = await async_client.post("/api/v1/profiles/sync", json=sync_payload, headers=USER_A_HEADERS)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["full_name"] == "Priya Sharma (Updated)"
