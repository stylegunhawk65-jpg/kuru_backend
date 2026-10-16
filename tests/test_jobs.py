"""Tests for Job Search, Transparent Matching, Saved Jobs, and User Isolation."""

from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobPosting, SavedJob
from app.models.profile import StudentProfile
from app.models.skill import StudentSkill
from app.services.matcher import calculate_job_match, normalize_skill


# Mock token helper
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
    """Automatically mock token verification for job tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}


def test_normalize_skill():
    """Test skill normalization and alias resolution."""
    assert normalize_skill("PostgreSQL") == "postgresql"
    assert normalize_skill("Postgres") == "postgresql"
    assert normalize_skill("Node.js") == "node"
    assert normalize_skill("React.js") == "react"
    assert normalize_skill("Golang") == "go"
    assert normalize_skill("Kubernetes") == "kubernetes"
    assert normalize_skill("K8s") == "kubernetes"


def test_calculate_job_match_transparent_breakdown():
    """Test deterministic rule-based matching with explicit reasons."""
    # Create sample job
    job = JobPosting(
        id=str(uuid.uuid4()),
        source="curated_india",
        source_id="z_001",
        dedup_hash="hash_z001",
        title="Junior Backend Engineer (Go / Python)",
        company="Zerodha",
        location="Bengaluru, Karnataka, India",
        is_remote=False,
        job_type="full_time",
        description="High-scale financial backend systems using Python and Go with PostgreSQL.",
        url="https://zerodha.com/careers",
        required_skills=["Python", "Go", "PostgreSQL", "Docker"],
    )

    # Profile for User A
    profile = StudentProfile(
        id=str(uuid.uuid4()),
        firebase_uid="usr_alpha_12345",
        full_name="Alpha Candidate",
        target_roles=["Backend Developer", "Software Engineer"],
        preferred_locations=["Bengaluru", "Remote"],
        interests=["Distributed Systems", "Financial Tech"],
    )

    # Skills for User A
    skills = [
        StudentSkill(
            id=str(uuid.uuid4()),
            firebase_uid="usr_alpha_12345",
            skill_name="Python",
            category="Language",
            confidence_score=0.95,
        ),
        StudentSkill(
            id=str(uuid.uuid4()),
            firebase_uid="usr_alpha_12345",
            skill_name="PostgreSQL",
            category="Database",
            confidence_score=0.85,
        ),
    ]

    res = calculate_job_match(job, profile, skills)

    # 1. Skills: matched Python & PostgreSQL (2 out of 4). Docker & Go missing.
    assert "Python" in res.matched_skills
    assert "PostgreSQL" in res.matched_skills
    assert "Docker" in res.missing_skills
    assert "Go" in res.missing_skills

    # 2. Score should be positive and bounded
    assert 0.0 < res.match_score <= 100.0

    # 3. Match reasons must contain detailed explanations
    reasons_str = " ".join(res.match_reasons)
    assert "Skill match:" in reasons_str
    assert "Target role aligns" in reasons_str
    assert "Bengaluru" in reasons_str


def test_calculate_job_match_empty_profile_and_skills():
    """Test that missing profile or skills returns safe neutral baseline scores."""
    job = JobPosting(
        id=str(uuid.uuid4()),
        source="curated_india",
        source_id="dummy",
        dedup_hash="dummy_hash",
        title="Software Engineer",
        company="Generic Co",
        location="Remote",
        is_remote=True,
        job_type="full_time",
        description="General software engineering.",
        url="https://example.com/jobs",
        required_skills=[],
    )

    res = calculate_job_match(job, None, [])
    assert 0.0 <= res.match_score <= 100.0
    assert len(res.match_reasons) > 0


@pytest.mark.asyncio
async def test_jobs_unauthorized(async_client: AsyncClient):
    """Test accessing job endpoints without valid Firebase token returns 401."""
    res = await async_client.get("/api/v1/jobs")
    assert res.status_code == 401

    res = await async_client.get("/api/v1/jobs/saved")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_jobs_and_search(async_client: AsyncClient):
    """Test listing jobs with search, filtering, and personalized ranking."""
    # 1. Fetch initial list
    res = await async_client.get("/api/v1/jobs", headers=USER_A_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 10
    assert len(data["items"]) > 0

    first_item = data["items"][0]
    assert "id" in first_item
    assert "match_score" in first_item
    assert "match_reasons" in first_item
    assert "is_saved" in first_item
    assert first_item["is_saved"] is False

    # 2. Filter by query
    q_res = await async_client.get("/api/v1/jobs?query=Zerodha", headers=USER_A_HEADERS)
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert all("zerodha" in j["company"].lower() for j in q_data["items"])

    # 3. Filter by location
    loc_res = await async_client.get("/api/v1/jobs?location=Bengaluru", headers=USER_A_HEADERS)
    assert loc_res.status_code == 200
    loc_data = loc_res.json()
    assert all("bengaluru" in j["location"].lower() for j in loc_data["items"])

    # 4. Filter by job_type
    intern_res = await async_client.get("/api/v1/jobs?job_type=internship", headers=USER_A_HEADERS)
    assert intern_res.status_code == 200
    intern_data = intern_res.json()
    assert all(j["job_type"] == "internship" for j in intern_data["items"])

    # 5. Filter by skill
    skill_res = await async_client.get("/api/v1/jobs?skill=Python", headers=USER_A_HEADERS)
    assert skill_res.status_code == 200
    skill_data = skill_res.json()
    assert all(any("python" in s.lower() for s in j["required_skills"]) for j in skill_data["items"])


@pytest.mark.asyncio
async def test_get_job_details_and_not_found(async_client: AsyncClient):
    """Test retrieving details for a single job and 404 for nonexistent job."""
    list_res = await async_client.get("/api/v1/jobs", headers=USER_A_HEADERS)
    job_id = list_res.json()["items"][0]["id"]

    res = await async_client.get(f"/api/v1/jobs/{job_id}", headers=USER_A_HEADERS)
    assert res.status_code == 200
    details = res.json()
    assert details["id"] == job_id
    assert "match_score" in details
    assert isinstance(details["match_reasons"], list)

    # Not found
    fake_id = str(uuid.uuid4())
    nf_res = await async_client.get(f"/api/v1/jobs/{fake_id}", headers=USER_A_HEADERS)
    assert nf_res.status_code == 404


@pytest.mark.asyncio
async def test_saved_jobs_crud_and_user_isolation(async_client: AsyncClient):
    """Test bookmarking, updating, deleting saved jobs and per-user data isolation."""
    # 1. User A bookmarks a job
    list_res = await async_client.get("/api/v1/jobs", headers=USER_A_HEADERS)
    job_id = list_res.json()["items"][0]["id"]

    save_payload = {"notes": "High priority backend role", "status": "saved"}
    save_res = await async_client.post(
        f"/api/v1/jobs/{job_id}/save",
        json=save_payload,
        headers=USER_A_HEADERS,
    )
    assert save_res.status_code == 201
    saved_data = save_res.json()
    assert saved_data["job_id"] == job_id
    assert saved_data["status"] == "saved"
    assert saved_data["notes"] == "High priority backend role"
    assert saved_data["job"]["id"] == job_id

    # 2. Verify job now shows is_saved = True for User A
    detail_res_a = await async_client.get(f"/api/v1/jobs/{job_id}", headers=USER_A_HEADERS)
    assert detail_res_a.json()["is_saved"] is True

    # 3. User B should NOT see this job as saved (per-user isolation)
    detail_res_b = await async_client.get(f"/api/v1/jobs/{job_id}", headers=USER_B_HEADERS)
    assert detail_res_b.json()["is_saved"] is False

    # 4. User A lists saved jobs -> has 1 item
    saved_list_a = await async_client.get("/api/v1/jobs/saved", headers=USER_A_HEADERS)
    assert saved_list_a.status_code == 200
    assert len(saved_list_a.json()) == 1
    assert saved_list_a.json()[0]["job_id"] == job_id

    # 5. User B lists saved jobs -> has 0 items
    saved_list_b = await async_client.get("/api/v1/jobs/saved", headers=USER_B_HEADERS)
    assert saved_list_b.status_code == 200
    assert len(saved_list_b.json()) == 0

    # 6. User B cannot update User A's saved job
    patch_b = await async_client.patch(
        f"/api/v1/jobs/saved/{job_id}",
        json={"notes": "Malicious override"},
        headers=USER_B_HEADERS,
    )
    assert patch_b.status_code == 404

    # 7. User A updates tracking status
    patch_a = await async_client.patch(
        f"/api/v1/jobs/saved/{job_id}",
        json={"status": "applied", "notes": "Applied via official portal"},
        headers=USER_A_HEADERS,
    )
    assert patch_a.status_code == 200
    assert patch_a.json()["status"] == "applied"
    assert patch_a.json()["notes"] == "Applied via official portal"

    # 8. User B cannot delete User A's bookmark
    del_b = await async_client.delete(f"/api/v1/jobs/{job_id}/save", headers=USER_B_HEADERS)
    assert del_b.status_code == 404

    # 9. User A unsaves job
    del_a = await async_client.delete(f"/api/v1/jobs/{job_id}/save", headers=USER_A_HEADERS)
    assert del_a.status_code == 204

    # 10. User A saved list is now empty
    saved_list_a_after = await async_client.get("/api/v1/jobs/saved", headers=USER_A_HEADERS)
    assert len(saved_list_a_after.json()) == 0


@pytest.mark.asyncio
async def test_sources_status_and_sync_endpoints(async_client: AsyncClient):
    """Test source health metrics and manual sync trigger endpoints."""
    # Status endpoint
    status_res = await async_client.get("/api/v1/jobs/sources/status", headers=USER_A_HEADERS)
    assert status_res.status_code == 200
    statuses = status_res.json()
    assert isinstance(statuses, list)
    assert len(statuses) >= 5

    # Trigger single source sync
    sync_res = await async_client.post(
        "/api/v1/jobs/sources/sync?source_name=curated_india",
        headers=USER_A_HEADERS,
    )
    assert sync_res.status_code == 200
    assert "curated_india" in sync_res.json()["results"]

    # Trigger invalid source sync -> 404
    bad_sync = await async_client.post(
        "/api/v1/jobs/sources/sync?source_name=non_existent_provider",
        headers=USER_A_HEADERS,
    )
    assert bad_sync.status_code == 404
