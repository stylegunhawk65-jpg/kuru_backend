"""Tests for Student Career Profile CRUD endpoints and per-user data isolation."""

from unittest.mock import patch
import pytest
from httpx import AsyncClient

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
    """Automatically mock token verification for profile tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}

SAMPLE_PROFILE_PAYLOAD = {
    "full_name": "Aarav Sharma",
    "email": "aarav.sharma@example.edu",
    "education": [
        {
            "institution": "Indian Institute of Technology, Bombay",
            "degree": "B.Tech",
            "field_of_study": "Computer Science and Engineering",
            "start_year": 2022,
            "end_year": 2026,
            "grade_or_cgpa": "8.8/10",
        }
    ],
    "interests": ["Machine Learning", "Distributed Systems", "Cloud Computing"],
    "target_roles": ["Software Engineer", "Backend Developer", "ML Engineer"],
    "preferred_locations": ["Bengaluru", "Hyderabad", "Pune", "Remote"],
    "bio": "Third-year CSE undergraduate passionate about large-scale backend systems.",
}


@pytest.mark.asyncio
async def test_create_student_profile_success(async_client: AsyncClient):
    """Test creating a career profile with valid schema."""
    response = await async_client.post(
        "/api/v1/profiles",
        json=SAMPLE_PROFILE_PAYLOAD,
        headers=USER_A_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["firebase_uid"] == "usr_alpha_12345"
    assert data["full_name"] == "Aarav Sharma"
    assert data["email"] == "aarav.sharma@example.edu"
    assert len(data["education"]) == 1
    assert data["education"][0]["institution"] == "Indian Institute of Technology, Bombay"
    assert "Machine Learning" in data["interests"]
    assert "Bengaluru" in data["preferred_locations"]
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


@pytest.mark.asyncio
async def test_create_duplicate_profile_conflict(async_client: AsyncClient):
    """Ensure duplicate profile creation for the same user returns 409 Conflict."""
    # First creation
    res1 = await async_client.post(
        "/api/v1/profiles",
        json=SAMPLE_PROFILE_PAYLOAD,
        headers=USER_A_HEADERS,
    )
    assert res1.status_code == 201

    # Second creation attempt
    res2 = await async_client.post(
        "/api/v1/profiles",
        json=SAMPLE_PROFILE_PAYLOAD,
        headers=USER_A_HEADERS,
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_create_profile_validation_failures(async_client: AsyncClient):
    """Ensure invalid payloads trigger 422 Unprocessable Entity."""
    # Missing full_name
    invalid_payload_1 = {**SAMPLE_PROFILE_PAYLOAD}
    del invalid_payload_1["full_name"]
    res1 = await async_client.post(
        "/api/v1/profiles",
        json=invalid_payload_1,
        headers=USER_A_HEADERS,
    )
    assert res1.status_code == 422

    # Empty full_name
    invalid_payload_2 = {**SAMPLE_PROFILE_PAYLOAD, "full_name": ""}
    res2 = await async_client.post(
        "/api/v1/profiles",
        json=invalid_payload_2,
        headers=USER_A_HEADERS,
    )
    assert res2.status_code == 422

    # Invalid email format
    invalid_payload_3 = {**SAMPLE_PROFILE_PAYLOAD, "email": "not-an-email"}
    res3 = await async_client.post(
        "/api/v1/profiles",
        json=invalid_payload_3,
        headers=USER_A_HEADERS,
    )
    assert res3.status_code == 422

    # Invalid year in education
    invalid_payload_4 = {
        **SAMPLE_PROFILE_PAYLOAD,
        "education": [{"institution": "IIT", "degree": "B.Tech", "start_year": 1800}],
    }
    res4 = await async_client.post(
        "/api/v1/profiles",
        json=invalid_payload_4,
        headers=USER_A_HEADERS,
    )
    assert res4.status_code == 422


@pytest.mark.asyncio
async def test_get_my_profile_lifecycle(async_client: AsyncClient):
    """Test retrieving student profile via /api/v1/profiles/me."""
    # Prior to creation -> 404
    get_res_before = await async_client.get("/api/v1/profiles/me", headers=USER_A_HEADERS)
    assert get_res_before.status_code == 404

    # Create profile
    create_res = await async_client.post(
        "/api/v1/profiles",
        json=SAMPLE_PROFILE_PAYLOAD,
        headers=USER_A_HEADERS,
    )
    assert create_res.status_code == 201

    # After creation -> 200
    get_res_after = await async_client.get("/api/v1/profiles/me", headers=USER_A_HEADERS)
    assert get_res_after.status_code == 200
    assert get_res_after.json()["full_name"] == "Aarav Sharma"
    assert get_res_after.json()["firebase_uid"] == "usr_alpha_12345"


@pytest.mark.asyncio
async def test_update_my_profile(async_client: AsyncClient):
    """Test partial update of profile attributes."""
    await async_client.post(
        "/api/v1/profiles",
        json=SAMPLE_PROFILE_PAYLOAD,
        headers=USER_A_HEADERS,
    )

    update_payload = {
        "bio": "Updated bio with AI research experience.",
        "target_roles": ["Principal ML Architect"],
        "preferred_locations": ["Remote", "Bengaluru"],
    }

    put_res = await async_client.put(
        "/api/v1/profiles/me",
        json=update_payload,
        headers=USER_A_HEADERS,
    )
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["bio"] == "Updated bio with AI research experience."
    assert data["target_roles"] == ["Principal ML Architect"]
    assert data["preferred_locations"] == ["Remote", "Bengaluru"]
    # Unchanged fields remain preserved
    assert data["full_name"] == "Aarav Sharma"


@pytest.mark.asyncio
async def test_update_nonexistent_profile_returns_404(async_client: AsyncClient):
    """Ensure update fails with 404 when user has no profile."""
    res = await async_client.put(
        "/api/v1/profiles/me",
        json={"bio": "New bio"},
        headers=USER_A_HEADERS,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_my_profile_lifecycle(async_client: AsyncClient):
    """Test deletion of profile and subsequent 404 checks."""
    # Create profile
    await async_client.post(
        "/api/v1/profiles",
        json=SAMPLE_PROFILE_PAYLOAD,
        headers=USER_A_HEADERS,
    )

    # Delete profile
    del_res = await async_client.delete("/api/v1/profiles/me", headers=USER_A_HEADERS)
    assert del_res.status_code == 204

    # Subsequent GET must return 404
    get_res = await async_client.get("/api/v1/profiles/me", headers=USER_A_HEADERS)
    assert get_res.status_code == 404

    # Subsequent DELETE must return 404
    del_res_again = await async_client.delete("/api/v1/profiles/me", headers=USER_A_HEADERS)
    assert del_res_again.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_data_isolation(async_client: AsyncClient):
    """Ensure User A cannot view, mutate, or access User B's profile data."""
    # 1. User A creates their profile
    res_a = await async_client.post(
        "/api/v1/profiles",
        json=SAMPLE_PROFILE_PAYLOAD,
        headers=USER_A_HEADERS,
    )
    assert res_a.status_code == 201
    user_a_profile_id = res_a.json()["id"]

    # 2. User B queries their own profile -> must get 404 (does NOT see User A)
    res_b_me = await async_client.get("/api/v1/profiles/me", headers=USER_B_HEADERS)
    assert res_b_me.status_code == 404

    # 3. User B attempts to access User A's profile by ID -> must get 404
    res_b_access_a = await async_client.get(
        f"/api/v1/profiles/{user_a_profile_id}",
        headers=USER_B_HEADERS,
    )
    assert res_b_access_a.status_code == 404

    # 4. User B creates their own profile with different information
    user_b_payload = {
        **SAMPLE_PROFILE_PAYLOAD,
        "full_name": "Diya Patel",
        "email": "diya.patel@example.edu",
        "target_roles": ["DevOps Engineer", "Site Reliability Engineer"],
    }
    res_b_create = await async_client.post(
        "/api/v1/profiles",
        json=user_b_payload,
        headers=USER_B_HEADERS,
    )
    assert res_b_create.status_code == 201
    assert res_b_create.json()["firebase_uid"] == "usr_bravo_67890"

    # 5. User A updates their profile -> User B's profile remains untouched
    await async_client.put(
        "/api/v1/profiles/me",
        json={"bio": "Alpha updated bio"},
        headers=USER_A_HEADERS,
    )

    check_b = await async_client.get("/api/v1/profiles/me", headers=USER_B_HEADERS)
    assert check_b.status_code == 200
    assert check_b.json()["full_name"] == "Diya Patel"
    assert check_b.json()["bio"] != "Alpha updated bio"

    # 6. User A deletes their profile -> User B's profile continues to exist
    del_a = await async_client.delete("/api/v1/profiles/me", headers=USER_A_HEADERS)
    assert del_a.status_code == 204

    still_exists_b = await async_client.get("/api/v1/profiles/me", headers=USER_B_HEADERS)
    assert still_exists_b.status_code == 200
    assert still_exists_b.json()["full_name"] == "Diya Patel"
