"""Integration tests for GitHub endpoints, static repository analysis, and skill graphs."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

# Mock tokens and headers
USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}

MOCK_GH_USER = {
    "id": 987654,
    "login": "octocat-student",
    "avatar_url": "https://avatars.githubusercontent.com/u/987654",
}

MOCK_GH_REPOS = [
    {
        "id": 111222,
        "name": "career-twin-core",
        "full_name": "octocat-student/career-twin-core",
        "private": False,
        "html_url": "https://github.com/octocat-student/career-twin-core",
        "description": "Backend engine for student career twin",
        "default_branch": "main",
        "language": "Python",
        "stargazers_count": 12,
        "forks_count": 2,
    }
]

MOCK_TREE = [
    {"path": "requirements.txt", "type": "blob"},
    {"path": "Dockerfile", "type": "blob"},
    {"path": "main.py", "type": "blob"},
]

REQUIREMENTS_CONTENT = """
fastapi>=0.115.0
sqlalchemy>=2.0.30
asyncpg>=0.29.0
"""

MAIN_PY_CONTENT = """
from fastapi import FastAPI
import sqlalchemy

app = FastAPI()
"""


def mock_verify_token(token: str, *args, **kwargs):
    if token == "token_user_a":
        return {"uid": "usr_alpha_12345", "email": "alpha@example.com"}
    elif token == "token_user_b":
        return {"uid": "usr_bravo_67890", "email": "bravo@example.com"}
    raise ValueError("Unrecognized test token")


@pytest.fixture(autouse=True)
def setup_auth_and_github_mocks():
    """Mock Firebase auth token verification and external GitHub API calls."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


@pytest.mark.asyncio
async def test_connect_github_success_no_token_leak(async_client: AsyncClient):
    """Ensure connecting GitHub returns connection metadata and NEVER leaks the access token."""
    with patch("app.services.github_client.GitHubClient.get_current_user", new_callable=AsyncMock) as mock_user:
        mock_user.return_value = MOCK_GH_USER

        response = await async_client.post(
            "/api/v1/github/connect",
            json={"token": "ghp_secret_personal_access_token_123"},
            headers=USER_A_HEADERS,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_connected"] is True
        assert data["github_username"] == "octocat-student"
        assert data["github_user_id"] == "987654"
        assert data["avatar_url"] == "https://avatars.githubusercontent.com/u/987654"
        # Security invariant: token must never be present in the response
        assert "token" not in data
        assert "access_token" not in data
        assert "ghp_secret" not in str(data)


@pytest.mark.asyncio
async def test_github_status_and_disconnect(async_client: AsyncClient):
    """Test connection status check and clean disconnection."""
    with patch("app.services.github_client.GitHubClient.get_current_user", new_callable=AsyncMock) as mock_user:
        mock_user.return_value = MOCK_GH_USER

        # 1. Connect
        await async_client.post(
            "/api/v1/github/connect",
            json={"token": "ghp_token_xyz"},
            headers=USER_A_HEADERS,
        )

        # 2. Check Status
        status_res = await async_client.get("/api/v1/github/status", headers=USER_A_HEADERS)
        assert status_res.status_code == 200
        assert status_res.json()["is_connected"] is True

        # 3. Disconnect
        del_res = await async_client.delete("/api/v1/github/disconnect", headers=USER_A_HEADERS)
        assert del_res.status_code == 204

        # 4. Status is now disconnected
        status_res_after = await async_client.get("/api/v1/github/status", headers=USER_A_HEADERS)
        assert status_res_after.status_code == 200
        assert status_res_after.json()["is_connected"] is False


@pytest.mark.asyncio
async def test_github_repos_disconnected_returns_400(async_client: AsyncClient):
    """Ensure calling /repos without connecting GitHub returns 400 Bad Request."""
    response = await async_client.get("/api/v1/github/repos", headers=USER_A_HEADERS)
    assert response.status_code == 400
    assert "not connected" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_github_repos_list_and_select(async_client: AsyncClient):
    """Test listing user repositories and selecting them for analysis."""
    with patch("app.services.github_client.GitHubClient.get_current_user", new_callable=AsyncMock) as mock_user, \
         patch("app.services.github_client.GitHubClient.list_repositories", new_callable=AsyncMock) as mock_repos:
        mock_user.return_value = MOCK_GH_USER
        mock_repos.return_value = MOCK_GH_REPOS

        # Connect
        await async_client.post(
            "/api/v1/github/connect",
            json={"token": "ghp_valid_token"},
            headers=USER_A_HEADERS,
        )

        # List Repos
        list_res = await async_client.get("/api/v1/github/repos", headers=USER_A_HEADERS)
        assert list_res.status_code == 200
        repos = list_res.json()["repositories"]
        assert len(repos) == 1
        assert repos[0]["name"] == "career-twin-core"

        # Select Repo
        select_res = await async_client.post(
            "/api/v1/github/repos/select",
            json={"repo_ids": ["111222"]},
            headers=USER_A_HEADERS,
        )
        assert select_res.status_code == 200
        assert len(select_res.json()) == 1
        assert select_res.json()[0]["selected_for_analysis"] is True


@pytest.mark.asyncio
async def test_github_analysis_skills_and_graph(async_client: AsyncClient):
    """Test static analysis pipeline, skill extraction, and skill graph generation."""
    with patch("app.services.github_client.GitHubClient.get_current_user", new_callable=AsyncMock) as mock_user, \
         patch("app.services.github_client.GitHubClient.list_repositories", new_callable=AsyncMock) as mock_repos, \
         patch("app.services.github_client.GitHubClient.get_repository_languages", new_callable=AsyncMock) as mock_lang, \
         patch("app.services.github_client.GitHubClient.get_repository_tree", new_callable=AsyncMock) as mock_tree, \
         patch("app.services.github_client.GitHubClient.get_file_content", new_callable=AsyncMock) as mock_content:

        mock_user.return_value = MOCK_GH_USER
        mock_repos.return_value = MOCK_GH_REPOS
        mock_lang.return_value = {"Python": 50000, "HTML/CSS": 5000}
        mock_tree.return_value = MOCK_TREE

        async def fake_content(owner, repo, path, ref="main"):
            if "requirements.txt" in path:
                return REQUIREMENTS_CONTENT
            if "main.py" in path:
                return MAIN_PY_CONTENT
            return None

        mock_content.side_effect = fake_content

        # 1. Connect and select repo
        await async_client.post(
            "/api/v1/github/connect",
            json={"token": "ghp_valid_token"},
            headers=USER_A_HEADERS,
        )
        await async_client.post(
            "/api/v1/github/repos/select",
            json={"repo_ids": ["111222"]},
            headers=USER_A_HEADERS,
        )

        # 2. Trigger static analysis
        analyze_res = await async_client.post(
            "/api/v1/github/analyze",
            json={},
            headers=USER_A_HEADERS,
        )
        assert analyze_res.status_code == 200
        data = analyze_res.json()
        assert data["total_analyzed"] == 1
        analysis_id = data["analyses"][0]["id"]

        # 3. Fetch specific analysis details by ID
        detail_res = await async_client.get(f"/api/v1/github/analysis/{analysis_id}", headers=USER_A_HEADERS)
        assert detail_res.status_code == 200
        assert detail_res.json()["status"] == "completed"

        # 4. Fetch extracted student skills
        skills_res = await async_client.get("/api/v1/skills", headers=USER_A_HEADERS)
        assert skills_res.status_code == 200
        skills = skills_res.json()
        skill_names = [s["skill_name"] for s in skills]

        assert "Python" in skill_names
        assert "FastAPI" in skill_names
        assert "SQLAlchemy" in skill_names
        assert "Docker" in skill_names

        # Verify evidence reference structure
        fastapi_skill = next(s for s in skills if s["skill_name"] == "FastAPI")
        assert len(fastapi_skill["evidence"]) >= 1
        assert any("requirements.txt" in e["file_path"] for e in fastapi_skill["evidence"])

        # 5. Fetch skill knowledge graph
        graph_res = await async_client.get("/api/v1/skills/graph", headers=USER_A_HEADERS)
        assert graph_res.status_code == 200
        graph = graph_res.json()
        assert graph["total_skills"] >= 4

        # Verify relationship edge: FastAPI -> Python
        edge_pairs = [(e["source"], e["target"]) for e in graph["edges"]]
        assert ("FastAPI", "Python") in edge_pairs


@pytest.mark.asyncio
async def test_cross_user_isolation_github_and_skills(async_client: AsyncClient):
    """Ensure User A's GitHub connection, repositories, analyses, and skills are invisible to User B."""
    with patch("app.services.github_client.GitHubClient.get_current_user", new_callable=AsyncMock) as mock_user, \
         patch("app.services.github_client.GitHubClient.list_repositories", new_callable=AsyncMock) as mock_repos, \
         patch("app.services.github_client.GitHubClient.get_repository_languages", new_callable=AsyncMock) as mock_lang, \
         patch("app.services.github_client.GitHubClient.get_repository_tree", new_callable=AsyncMock) as mock_tree, \
         patch("app.services.github_client.GitHubClient.get_file_content", new_callable=AsyncMock) as mock_content:

        mock_user.return_value = MOCK_GH_USER
        mock_repos.return_value = MOCK_GH_REPOS
        mock_lang.return_value = {"Python": 20000}
        mock_tree.return_value = [{"path": "requirements.txt", "type": "blob"}]
        mock_content.return_value = "fastapi>=0.115.0\n"

        # 1. User A connects and runs analysis
        await async_client.post("/api/v1/github/connect", json={"token": "ghp_alpha"}, headers=USER_A_HEADERS)
        await async_client.post("/api/v1/github/repos/select", json={"repo_ids": ["111222"]}, headers=USER_A_HEADERS)
        res_a_analyze = await async_client.post("/api/v1/github/analyze", json={}, headers=USER_A_HEADERS)
        user_a_analysis_id = res_a_analyze.json()["analyses"][0]["id"]

        # 2. User B checks GitHub connection -> must be disconnected
        res_b_status = await async_client.get("/api/v1/github/status", headers=USER_B_HEADERS)
        assert res_b_status.json()["is_connected"] is False

        # 3. User B checks skills -> must be empty (cannot see User A's skills)
        res_b_skills = await async_client.get("/api/v1/skills", headers=USER_B_HEADERS)
        assert len(res_b_skills.json()) == 0

        # 4. User B checks skill graph -> must be empty
        res_b_graph = await async_client.get("/api/v1/skills/graph", headers=USER_B_HEADERS)
        assert res_b_graph.json()["total_skills"] == 0
        assert len(res_b_graph.json()["edges"]) == 0

        # 5. User B tries to access User A's analysis record by ID -> must get 404
        res_b_access_analysis = await async_client.get(
            f"/api/v1/github/analysis/{user_a_analysis_id}",
            headers=USER_B_HEADERS,
        )
        assert res_b_access_analysis.status_code == 404
