"""Tests for Cloud Firestore mobile sync endpoints, user isolation, and security rules."""

from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.services.firestore import FirestoreAccessDenied, firestore_service


# Mock token helper matching the project convention
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
    """Automatically mock token verification for Firestore tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


@pytest.fixture(autouse=True)
def clean_firestore_memory_store():
    """Ensure in-memory Firestore cache is cleared before each test."""
    firestore_service._memory_store.clear()
    yield
    firestore_service._memory_store.clear()


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(async_client: AsyncClient):
    """Ensure unauthenticated requests to Firestore sync endpoints return 401 Unauthorized."""
    endpoints = [
        ("GET", "/api/v1/sync/preferences"),
        ("PUT", "/api/v1/sync/preferences"),
        ("GET", "/api/v1/sync/notes"),
        ("POST", "/api/v1/sync/notes"),
        ("DELETE", "/api/v1/sync/notes/sample_note_id"),
    ]

    for method, path in endpoints:
        if method == "GET":
            response = await async_client.get(path)
        elif method == "PUT":
            response = await async_client.put(path, json={"weekly_study_goal_hours": 10})
        elif method == "POST":
            response = await async_client.post(path, json={"title": "Test", "content": "Test content"})
        elif method == "DELETE":
            response = await async_client.delete(path)

        assert response.status_code == 401, f"{method} {path} should return 401"
        assert "Authentication required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_preferences_lifecycle_and_isolation(async_client: AsyncClient):
    """Test user preferences PUT and GET endpoints and per-user data isolation."""
    # 1. User A initial preferences are empty
    get_res_a = await async_client.get("/api/v1/sync/preferences", headers=USER_A_HEADERS)
    assert get_res_a.status_code == 200
    assert get_res_a.json() == {}

    # 2. User A updates preferences
    put_res_a = await async_client.put(
        "/api/v1/sync/preferences",
        headers=USER_A_HEADERS,
        json={
            "theme_mode": "dark",
            "notifications_enabled": True,
            "weekly_study_goal_hours": 20,
            "preferred_role": "Backend Engineer",
            "custom_settings": {"sound_effects": False},
        },
    )
    assert put_res_a.status_code == 200
    data_a = put_res_a.json()
    assert data_a["weekly_study_goal_hours"] == 20
    assert data_a["preferred_role"] == "Backend Engineer"
    assert data_a["firebase_uid"] == "usr_alpha_12345"

    # 3. User A verifies saved preferences
    fetch_res_a = await async_client.get("/api/v1/sync/preferences", headers=USER_A_HEADERS)
    assert fetch_res_a.status_code == 200
    assert fetch_res_a.json()["weekly_study_goal_hours"] == 20

    # 4. User B queries preferences - should NOT see User A's data (Isolation)
    fetch_res_b = await async_client.get("/api/v1/sync/preferences", headers=USER_B_HEADERS)
    assert fetch_res_b.status_code == 200
    assert fetch_res_b.json() == {}


@pytest.mark.asyncio
async def test_career_notes_crud_and_isolation(async_client: AsyncClient):
    """Test personal career notes CRUD operations and per-user isolation."""
    # 1. User A creates a career note
    create_res = await async_client.post(
        "/api/v1/sync/notes",
        headers=USER_A_HEADERS,
        json={
            "title": "System Design: Database Indexing",
            "content": "B-Tree vs LSM-Tree trade-offs for write-heavy workloads.",
            "tags": ["databases", "indexing", "system-design"],
        },
    )
    assert create_res.status_code == 201
    note_data = create_res.json()
    assert note_data["title"] == "System Design: Database Indexing"
    assert note_data["firebase_uid"] == "usr_alpha_12345"
    note_id = note_data["id"]

    # 2. User A lists notes - should contain 1 note
    list_res_a = await async_client.get("/api/v1/sync/notes", headers=USER_A_HEADERS)
    assert list_res_a.status_code == 200
    notes_a = list_res_a.json()
    assert len(notes_a) == 1
    assert notes_a[0]["id"] == note_id

    # 3. User B lists notes - should be EMPTY (strict per-user isolation)
    list_res_b = await async_client.get("/api/v1/sync/notes", headers=USER_B_HEADERS)
    assert list_res_b.status_code == 200
    assert len(list_res_b.json()) == 0

    # 4. User A deletes note
    del_res = await async_client.delete(f"/api/v1/sync/notes/{note_id}", headers=USER_A_HEADERS)
    assert del_res.status_code == 200
    assert del_res.json() == {"deleted": True}

    # 5. User A verifies note is gone
    list_after_del = await async_client.get("/api/v1/sync/notes", headers=USER_A_HEADERS)
    assert len(list_after_del.json()) == 0

    # 6. Deleting non-existent note returns 404
    del_again = await async_client.delete(f"/api/v1/sync/notes/{note_id}", headers=USER_A_HEADERS)
    assert del_again.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_access_attempts_rejected_with_403(async_client: AsyncClient):
    """Ensure explicit cross-user access attempts (tampering target_uid) return 403 Forbidden."""
    # User A tries to view User B's preferences
    res1 = await async_client.get(
        "/api/v1/sync/preferences?target_uid=usr_bravo_67890",
        headers=USER_A_HEADERS,
    )
    assert res1.status_code == 403
    assert "Cross-user access denied" in res1.json()["detail"]

    # User A tries to modify User B's preferences
    res2 = await async_client.put(
        "/api/v1/sync/preferences?target_uid=usr_bravo_67890",
        headers=USER_A_HEADERS,
        json={"weekly_study_goal_hours": 30},
    )
    assert res2.status_code == 403
    assert "Cross-user access denied" in res2.json()["detail"]

    # User A tries to list User B's notes
    res3 = await async_client.get(
        "/api/v1/sync/notes?target_uid=usr_bravo_67890",
        headers=USER_A_HEADERS,
    )
    assert res3.status_code == 403
    assert "Cross-user access denied" in res3.json()["detail"]

    # User A tries to create a note in User B's collection
    res4 = await async_client.post(
        "/api/v1/sync/notes?target_uid=usr_bravo_67890",
        headers=USER_A_HEADERS,
        json={"title": "Hacked", "content": "Infiltrated notes"},
    )
    assert res4.status_code == 403
    assert "Cross-user access denied" in res4.json()["detail"]

    # User A tries to delete a note under User B's path
    res5 = await async_client.delete(
        "/api/v1/sync/notes/dummy_id?target_uid=usr_bravo_67890",
        headers=USER_A_HEADERS,
    )
    assert res5.status_code == 403
    assert "Cross-user access denied" in res5.json()["detail"]


@pytest.mark.asyncio
async def test_firestore_service_unit_isolation_guarantee():
    """Unit test for FirestoreService._ensure_user_match direct exceptions."""
    # Empty uid
    with pytest.raises(FirestoreAccessDenied):
        firestore_service._ensure_user_match("", "usr_bravo_67890")

    # Mismatch uid
    with pytest.raises(FirestoreAccessDenied):
        firestore_service._ensure_user_match("usr_alpha_12345", "usr_bravo_67890")

    # Matching uid succeeds without exception
    firestore_service._ensure_user_match("usr_alpha_12345", "usr_alpha_12345")
