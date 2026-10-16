"""Tests for Phase 8 SkillProof Engine: skill detection, code mapping, similarity, and honest reporting."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_token
from app.models.github import GithubConnection, GithubRepository
from app.models.skillproof import SkillProofEvidence, SkillProofRun
from app.services.github_client import GitHubClient
from app.services.skillproof.detector import (
    SkillDetectorAndMapper,
    detect_file_language,
    is_irrelevant_file,
)
from app.services.skillproof.reference_corpus import (
    ReferenceSource,
    reference_registry,
)
from app.services.skillproof.similarity import similarity_engine


def mock_verify_token(token: str, *args, **kwargs):
    if token == "token_user_a":
        return {
            "uid": "usr_student_alpha",
            "email": "alpha@kuru.ai",
            "name": "Alpha Student",
        }
    elif token == "token_user_b":
        return {
            "uid": "usr_student_bravo",
            "email": "bravo@kuru.ai",
            "name": "Bravo Student",
        }
    raise ValueError("Invalid test token")


@pytest.fixture(autouse=True)
def patch_firebase_auth():
    """Mock Firebase authentication for SkillProof tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}


@pytest.fixture
async def setup_github_connection_user_a(db_session: AsyncSession):
    """Seed user A with a connected GitHub account and a tracked repository."""
    conn = GithubConnection(
        firebase_uid="usr_student_alpha",
        encrypted_access_token=encrypt_token("ghp_valid_test_token_12345"),
        github_user_id="10101",
        github_username="student-alpha",
        avatar_url="https://github.com/student-alpha.png",
        scopes=["repo", "read:user"],
    )
    db_session.add(conn)

    repo = GithubRepository(
        firebase_uid="usr_student_alpha",
        github_repo_id="998877",
        name="kuru-demo-repo",
        full_name="student-alpha/kuru-demo-repo",
        is_private=False,
        html_url="https://github.com/student-alpha/kuru-demo-repo",
        description="Demo student repo for SkillProof testing",
        default_branch="main",
        primary_language="Python",
        stars_count=3,
        forks_count=0,
        selected_for_analysis=True,
    )
    db_session.add(repo)
    await db_session.commit()
    return repo


@pytest.fixture
async def setup_github_connection_user_b(db_session: AsyncSession):
    """Seed user B with a connected GitHub account."""
    conn = GithubConnection(
        firebase_uid="usr_student_bravo",
        encrypted_access_token=encrypt_token("ghp_valid_test_token_67890"),
        github_user_id="20202",
        github_username="student-bravo",
        avatar_url="https://github.com/student-bravo.png",
        scopes=["repo", "read:user"],
    )
    db_session.add(conn)
    await db_session.commit()
    return conn


# -----------------------------------------------------------------------------
# 1. Unit Tests: Similarity Modalities & Provenance
# -----------------------------------------------------------------------------
def test_exact_similarity_calculation():
    """Verify exact block similarity detection."""
    code_a = "from fastapi import FastAPI\n\napp = FastAPI()\n"
    code_b = "from fastapi import FastAPI\napp = FastAPI()\n"

    score, matches = similarity_engine.calculate_exact_similarity(code_a, code_b)
    assert score > 0.8
    assert "app = FastAPI()" in matches


def test_normalized_similarity_calculation():
    """Verify normalized matching strips comments and standardizes whitespace."""
    code_a = """
    # This is a comment
    def add(a, b):
        // another comment style
        return a + b
    """
    code_b = """
    def add(a, b):
        return a + b
    """
    score, coverage = similarity_engine.calculate_normalized_similarity(code_a, code_b, "Python")
    assert score == 1.0
    assert coverage == 1.0


def test_token_similarity_calculation():
    """Verify token Jaccard similarity across variations in formatting."""
    code_a = "x = [1, 2, 3]\nprint(x)"
    code_b = "x = [\n  1,\n  2,\n  3\n]\nprint(x)"

    score = similarity_engine.calculate_token_similarity(code_a, code_b, "Python")
    assert score > 0.85


def test_ast_similarity_with_renamed_identifiers():
    """Verify structural AST similarity detects structure even when variable names are altered."""
    code_orig = """
class UserService:
    async def fetch_user(user_id: int):
        result = await query_db(user_id)
        return result
"""
    code_renamed = """
class AccountManager:
    async def retrieve_account(acc_id: int):
        data = await get_record(acc_id)
        return data
"""
    ast_score = similarity_engine.calculate_ast_similarity(code_orig, code_renamed)
    # The AST node structure (ClassDef, AsyncFunctionDef, Assign, Await, Return) is identical
    assert ast_score > 0.90


def test_missing_reference_corpus_explicit_reporting():
    """Verify unknown or unindexed skills report missing references rather than false 0%."""
    has_rust = reference_registry.has_references_for_skill("UnindexedCustomLib999")
    assert has_rust is False
    refs = reference_registry.get_references_for_skill("UnindexedCustomLib999")
    assert len(refs) == 0


def test_file_exclusion_and_language_detection():
    """Verify irrelevant files are filtered and language extensions are resolved."""
    assert is_irrelevant_file(".git/config") is True
    assert is_irrelevant_file("node_modules/express/index.js") is True
    assert is_irrelevant_file("venv/lib/site-packages/fastapi/__init__.py") is True
    assert is_irrelevant_file("package-lock.json") is True
    assert is_irrelevant_file("app/main.py") is False

    assert detect_file_language("app/api/endpoints.py") == "Python"
    assert detect_file_language("frontend/src/App.tsx") == "TypeScript"
    assert detect_file_language("Dockerfile") == "Dockerfile"
    assert detect_file_language("unknown.xyz") == "Unknown"


# -----------------------------------------------------------------------------
# 2. Unit Tests: Detector Distinguishing Dependency vs Implementation
# -----------------------------------------------------------------------------
def test_detector_distinguishes_dependency_and_implementation():
    """Verify skills are properly labeled dependency_only, implementation_only, or implemented."""
    detector = SkillDetectorAndMapper()

    # 1. Manifest declaring dependencies
    reqs = "fastapi==0.115.0\npydantic>=2.0\ncelery==5.3.0\n"
    detector.scan_manifest("requirements.txt", reqs)

    # 2. Source file implementing only FastAPI and Pydantic (NOT Celery)
    source = """
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel

class Item(BaseModel):
    name: str

app = FastAPI()
router = APIRouter()

@router.get("/items")
async def get_items():
    return []
"""
    detector.scan_source_file("app/main.py", source)

    skills = {s["skill_name"]: s for s in detector.get_detected_skills()}

    # FastAPI: declared in reqs AND implemented in main.py -> implemented
    assert "FastAPI" in skills
    assert skills["FastAPI"]["status"] == "implemented"
    assert skills["FastAPI"]["has_dependency_evidence"] is True
    assert skills["FastAPI"]["has_implementation_evidence"] is True
    assert "app/main.py" in skills["FastAPI"]["mapped_files"]

    # Celery: declared in reqs but NEVER implemented -> dependency_only
    assert "Celery" in skills
    assert skills["Celery"]["status"] == "dependency_only"
    assert skills["Celery"]["has_dependency_evidence"] is True
    assert skills["Celery"]["has_implementation_evidence"] is False
    assert "app/main.py" not in skills["Celery"]["mapped_files"]

    # Python: implemented in source code
    assert "Python" in skills
    assert skills["Python"]["has_implementation_evidence"] is True


def test_detector_overlapping_skills_in_same_file():
    """Verify multiple skills can overlap within the same source file."""
    detector = SkillDetectorAndMapper()
    source = """
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Schema(BaseModel):
    id: str

router = APIRouter()
"""
    detector.scan_source_file("app/api.py", source)
    file_skills = detector.get_file_skills()

    assert "app/api.py" in file_skills
    skills_in_file = {item["skill"] for item in file_skills["app/api.py"]}
    assert "FastAPI" in skills_in_file
    assert "Pydantic" in skills_in_file
    assert "SQLAlchemy" in skills_in_file


# -----------------------------------------------------------------------------
# 3. Endpoint Tests: Authentication & Authorization
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(async_client: AsyncClient):
    """Ensure all SkillProof endpoints return 401 when no token is provided."""
    endpoints = [
        ("GET", "/api/v1/skillproof/repos"),
        ("GET", "/api/v1/skillproof/repos/test-repo/skills"),
        ("POST", "/api/v1/skillproof/analyze"),
        ("GET", "/api/v1/skillproof/runs"),
        ("GET", "/api/v1/skillproof/runs/run-123"),
        ("DELETE", "/api/v1/skillproof/runs/run-123"),
    ]

    for method, url in endpoints:
        if method == "GET":
            res = await async_client.get(url)
        elif method == "POST":
            res = await async_client.post(url, json={"repo_id": "test-repo"})
        elif method == "DELETE":
            res = await async_client.delete(url)

        assert res.status_code == 401, f"{method} {url} should return 401"
        assert "Authentication required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_cross_user_isolation_on_runs(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Ensure User B cannot view or delete User A's SkillProof runs."""
    # Seed a run owned by User A
    run_a = SkillProofRun(
        firebase_uid="usr_student_alpha",
        repository_id="repo-user-a",
        repository_full_name="student-alpha/kuru-demo",
        target_skills=["FastAPI"],
        status="completed",
        summary={"skills_detected_count": 1, "average_similarity_score": 0.45},
        honest_reporting={"plagiarism_claim": False, "disclaimer": "Honest test"},
    )
    db_session.add(run_a)
    await db_session.commit()
    await db_session.refresh(run_a)

    # 1. User A can view their run
    res_a = await async_client.get(f"/api/v1/skillproof/runs/{run_a.id}", headers=USER_A_HEADERS)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == run_a.id

    # 2. User B gets 404 Not Found when trying to view User A's run (strict isolation)
    res_b = await async_client.get(f"/api/v1/skillproof/runs/{run_a.id}", headers=USER_B_HEADERS)
    assert res_b.status_code == 404

    # 3. User B gets 404 when trying to delete User A's run
    del_b = await async_client.delete(f"/api/v1/skillproof/runs/{run_a.id}", headers=USER_B_HEADERS)
    assert del_b.status_code == 404

    # 4. User B listing runs sees an empty list
    list_b = await async_client.get("/api/v1/skillproof/runs", headers=USER_B_HEADERS)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0


# -----------------------------------------------------------------------------
# 4. End-to-End Skill Detection & Targeted Analysis
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_detect_skills_endpoint(
    async_client: AsyncClient,
    setup_github_connection_user_a,
):
    """Test GET /api/v1/skillproof/repos/{repo_id}/skills endpoint."""
    mock_tree = [
        {"path": "requirements.txt", "type": "blob"},
        {"path": "app/main.py", "type": "blob"},
    ]
    mock_reqs = "fastapi==0.115.0\ncelery==5.3.0\n"
    mock_main = """
from fastapi import FastAPI
app = FastAPI()
@app.get("/")
def read_root():
    return {"status": "ok"}
"""

    with patch.object(GitHubClient, "get_repository_tree", new_callable=AsyncMock) as mock_get_tree, \
         patch.object(GitHubClient, "get_file_content", new_callable=AsyncMock) as mock_get_content:

        mock_get_tree.return_value = mock_tree

        async def file_content_side_effect(owner, repo, file_path, ref="main"):
            if file_path == "requirements.txt":
                return mock_reqs
            elif file_path == "app/main.py":
                return mock_main
            return None

        mock_get_content.side_effect = file_content_side_effect

        response = await async_client.get(
            "/api/v1/skillproof/repos/student-alpha/kuru-demo-repo/skills",
            headers=USER_A_HEADERS,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["repository_full_name"] == "student-alpha/kuru-demo-repo"
        assert data["implemented_count"] >= 1
        assert data["dependency_only_count"] >= 1

        skills = {s["skill_name"]: s for s in data["skills"]}
        assert skills["FastAPI"]["status"] == "implemented"
        assert skills["Celery"]["status"] == "dependency_only"


@pytest.mark.asyncio
async def test_targeted_skillproof_analysis_and_honest_reporting(
    async_client: AsyncClient,
    setup_github_connection_user_a,
):
    """Test targeted analysis POST /api/v1/skillproof/analyze with honest reporting guarantees."""
    mock_tree = [
        {"path": "requirements.txt", "type": "blob"},
        {"path": "app/api.py", "type": "blob"},
        {"path": "unrelated/style.css", "type": "blob"},
    ]
    mock_reqs = "fastapi==0.115.0\nredis==5.0.0\n"
    mock_api = """
from fastapi import FastAPI, APIRouter

app = FastAPI()
router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello World"}
"""

    with patch.object(GitHubClient, "get_repository_tree", new_callable=AsyncMock) as mock_get_tree, \
         patch.object(GitHubClient, "get_file_content", new_callable=AsyncMock) as mock_get_content:

        mock_get_tree.return_value = mock_tree

        async def file_content_side_effect(owner, repo, file_path, ref="main"):
            if file_path == "requirements.txt":
                return mock_reqs
            elif file_path == "app/api.py":
                return mock_api
            return None

        mock_get_content.side_effect = file_content_side_effect

        # 1. Targeted analysis specifying only "FastAPI"
        res = await async_client.post(
            "/api/v1/skillproof/analyze",
            headers=USER_A_HEADERS,
            json={
                "repo_id": "student-alpha/kuru-demo-repo",
                "selected_skills": ["FastAPI"],
                "max_files": 10,
            },
        )
        assert res.status_code == 201
        data = res.json()

        # Verify run metadata
        assert data["status"] == "completed"
        assert data["target_skills"] == ["FastAPI"]
        assert data["repository_full_name"] == "student-alpha/kuru-demo-repo"

        # Verify Honest Reporting
        honest = data["honest_reporting"]
        assert honest["plagiarism_claim"] is False
        assert honest["ai_generation_claim"] is False
        assert "not indicate plagiarism" in honest["disclaimer"].lower()

        # Verify Evidence Records
        evidence = data["evidence_records"]
        assert len(evidence) > 0

        # Verify Similarity Findings against reference corpus
        api_evidence = next((e for e in evidence if e["file_path"] == "app/api.py"), None)
        assert api_evidence is not None
        assert api_evidence["has_implementation"] is True

        # Has legitimate similarity finding against canonical FastAPI tutorial
        findings = api_evidence["similarity_findings"]
        assert len(findings) > 0
        first_finding = findings[0]
        assert first_finding["skill"] == "FastAPI"
        assert "MIT License" in first_finding["license"]
        assert "https://fastapi.tiangolo.com" in first_finding["canonical_url"]
        assert first_finding["similarity_score"] > 0.0


@pytest.mark.asyncio
async def test_empty_selection_analyzes_entire_repository(
    async_client: AsyncClient,
    setup_github_connection_user_a,
):
    """Test that empty or None selected_skills analyzes all detected skills across repo."""
    mock_tree = [
        {"path": "requirements.txt", "type": "blob"},
        {"path": "app/main.py", "type": "blob"},
    ]
    mock_reqs = "fastapi==0.115.0\n"
    mock_main = "from fastapi import FastAPI\napp = FastAPI()\n"

    with patch.object(GitHubClient, "get_repository_tree", new_callable=AsyncMock) as mock_get_tree, \
         patch.object(GitHubClient, "get_file_content", new_callable=AsyncMock) as mock_get_content:

        mock_get_tree.return_value = mock_tree

        async def file_content_side_effect(owner, repo, file_path, ref="main"):
            if file_path == "requirements.txt":
                return mock_reqs
            elif file_path == "app/main.py":
                return mock_main
            return None

        mock_get_content.side_effect = file_content_side_effect

        # Empty selected_skills
        res = await async_client.post(
            "/api/v1/skillproof/analyze",
            headers=USER_A_HEADERS,
            json={
                "repo_id": "student-alpha/kuru-demo-repo",
                "selected_skills": [],
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["summary"]["is_targeted_analysis"] is False
        assert data["summary"]["skills_detected_count"] >= 1
