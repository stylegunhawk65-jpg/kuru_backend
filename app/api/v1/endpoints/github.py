"""Authenticated GitHub integration endpoints: connection, repository selection, and static analysis."""

from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.security import decrypt_token, encrypt_token
from app.db.session import get_db
from app.models.github import GithubConnection, GithubRepository, RepositoryAnalysis
from app.models.skill import SkillGraphEdge, StudentSkill
from app.schemas.github import (
    AnalysisResultItem,
    GitHubAnalyzeRequest,
    GitHubAnalyzeResponse,
    GitHubConnectionResponse,
    GitHubConnectRequest,
    GitHubRepoItem,
    GitHubRepoListResponse,
    GitHubRepoSelectRequest,
)
from app.services.analyzer import RepositoryAnalyzer, build_skill_graph
from app.services.github_client import GitHubClient

logger = logging.getLogger("kuru.github")
router = APIRouter()


async def get_decrypted_github_token(
    current_user: AuthenticatedUser,
    db: AsyncSession,
) -> str:
    """Retrieve and decrypt the user's stored GitHub token. Raises 400 if disconnected."""
    stmt = select(GithubConnection).where(GithubConnection.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    conn = result.scalar_one_or_none()

    if not conn or not conn.encrypted_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account is not connected. Please connect via /api/v1/github/connect first.",
        )

    return decrypt_token(conn.encrypted_access_token)


@router.post(
    "/connect",
    response_model=GitHubConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect GitHub Account",
    description="Connect a GitHub token securely. The token is validated with GitHub, encrypted at rest, and never exposed in responses.",
)
async def connect_github(
    payload: GitHubConnectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GitHubConnectionResponse:
    """Validate and store GitHub credentials with symmetric encryption."""
    client = GitHubClient(token=payload.token)
    user_info = await client.get_current_user()

    encrypted = encrypt_token(payload.token)

    # Upsert connection record for current user
    stmt = select(GithubConnection).where(GithubConnection.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()

    if connection is None:
        connection = GithubConnection(
            firebase_uid=current_user.uid,
            encrypted_access_token=encrypted,
            github_user_id=str(user_info.get("id")),
            github_username=user_info.get("login"),
            avatar_url=user_info.get("avatar_url"),
            scopes=["repo", "read:user"],
        )
        db.add(connection)
    else:
        connection.encrypted_access_token = encrypted
        connection.github_user_id = str(user_info.get("id"))
        connection.github_username = user_info.get("login")
        connection.avatar_url = user_info.get("avatar_url")

    await db.commit()
    await db.refresh(connection)

    logger.info("User %s connected GitHub account %s", current_user.uid, connection.github_username)
    return GitHubConnectionResponse(
        is_connected=True,
        github_username=connection.github_username,
        github_user_id=connection.github_user_id,
        avatar_url=connection.avatar_url,
        scopes=connection.scopes,
        connected_at=connection.updated_at,
    )


@router.get(
    "/status",
    response_model=GitHubConnectionResponse,
    summary="Get GitHub Connection Status",
    description="Returns whether the authenticated user has an active GitHub connection.",
)
async def get_github_status(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GitHubConnectionResponse:
    """Report GitHub connection status without revealing the token."""
    stmt = select(GithubConnection).where(GithubConnection.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()

    if not connection or not connection.encrypted_access_token:
        return GitHubConnectionResponse(is_connected=False)

    return GitHubConnectionResponse(
        is_connected=True,
        github_username=connection.github_username,
        github_user_id=connection.github_user_id,
        avatar_url=connection.avatar_url,
        scopes=connection.scopes,
        connected_at=connection.updated_at,
    )


@router.delete(
    "/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect GitHub Account",
    description="Remove stored GitHub credentials and disconnect the integration.",
)
async def disconnect_github(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Disconnect and wipe encrypted GitHub access credentials."""
    stmt = select(GithubConnection).where(GithubConnection.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()

    if connection:
        await db.delete(connection)
        await db.commit()
        logger.info("Disconnected GitHub for user %s", current_user.uid)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/repos",
    response_model=GitHubRepoListResponse,
    summary="List User Repositories",
    description="List repositories accessible with user's GitHub token with pagination.",
)
async def list_github_repositories(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(30, ge=1, le=100, description="Items per page"),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GitHubRepoListResponse:
    """Fetch user repositories from GitHub and map tracking status."""
    token = await get_decrypted_github_token(current_user, db)
    client = GitHubClient(token=token)
    gh_repos = await client.list_repositories(page=page, per_page=per_page)

    # Check which repos are already tracked in database for this user
    stmt = select(GithubRepository).where(GithubRepository.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    tracked_repos = {r.github_repo_id: r for r in result.scalars().all()}

    repo_items = []
    for r in gh_repos:
        repo_id_str = str(r.get("id"))
        tracked = tracked_repos.get(repo_id_str)
        repo_items.append(
            GitHubRepoItem(
                id=tracked.id if tracked else None,
                github_repo_id=repo_id_str,
                name=r.get("name", ""),
                full_name=r.get("full_name", ""),
                is_private=r.get("private", False),
                html_url=r.get("html_url", ""),
                description=r.get("description"),
                default_branch=r.get("default_branch", "main"),
                primary_language=r.get("language"),
                stars_count=r.get("stargazers_count", 0),
                forks_count=r.get("forks_count", 0),
                selected_for_analysis=tracked.selected_for_analysis if tracked else False,
                last_analyzed_at=tracked.last_analyzed_at if tracked else None,
            )
        )

    return GitHubRepoListResponse(
        total=len(repo_items),
        page=page,
        per_page=per_page,
        repositories=repo_items,
    )


@router.post(
    "/repos/select",
    response_model=list[GitHubRepoItem],
    summary="Select Repositories for Analysis",
    description="Select specific repositories for static skill extraction.",
)
async def select_repositories(
    payload: GitHubRepoSelectRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GitHubRepoItem]:
    """Store user-selected repositories in the database for analysis."""
    token = await get_decrypted_github_token(current_user, db)
    client = GitHubClient(token=token)

    # Fetch accessible repos to find selected ones
    all_repos = await client.list_repositories(page=1, per_page=100)
    repo_map = {str(r.get("id")): r for r in all_repos}
    repo_map.update({r.get("full_name"): r for r in all_repos})

    saved_repos = []
    for target in payload.repo_ids:
        r = repo_map.get(str(target))
        if not r:
            continue

        repo_id_str = str(r.get("id"))
        # Check existing
        stmt = select(GithubRepository).where(
            GithubRepository.firebase_uid == current_user.uid,
            GithubRepository.github_repo_id == repo_id_str,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.selected_for_analysis = True
            saved_repos.append(existing)
        else:
            new_repo = GithubRepository(
                firebase_uid=current_user.uid,
                github_repo_id=repo_id_str,
                name=r.get("name", ""),
                full_name=r.get("full_name", ""),
                is_private=r.get("private", False),
                html_url=r.get("html_url", ""),
                description=r.get("description"),
                default_branch=r.get("default_branch", "main"),
                primary_language=r.get("language"),
                stars_count=r.get("stargazers_count", 0),
                forks_count=r.get("forks_count", 0),
                selected_for_analysis=True,
            )
            db.add(new_repo)
            saved_repos.append(new_repo)

    await db.commit()
    for repo in saved_repos:
        await db.refresh(repo)

    return [GitHubRepoItem.model_validate(r) for r in saved_repos]


@router.post(
    "/analyze",
    response_model=GitHubAnalyzeResponse,
    summary="Trigger Static Code Analysis",
    description="Analyze selected repositories safely via metadata, dependency manifests, and static AST parsing (zero untrusted code execution).",
)
async def analyze_repositories(
    payload: GitHubAnalyzeRequest | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GitHubAnalyzeResponse:
    """Execute static repository analysis and update student skill graph."""
    token = await get_decrypted_github_token(current_user, db)
    client = GitHubClient(token=token)

    # Query selected repositories for this user
    stmt = select(GithubRepository).where(
        GithubRepository.firebase_uid == current_user.uid,
        GithubRepository.selected_for_analysis.is_(True),
    )
    if payload and payload.repo_ids:
        stmt = stmt.where(GithubRepository.id.in_(payload.repo_ids))

    repositories = (await db.execute(stmt)).scalars().all()
    if not repositories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No selected repositories found for analysis. Please select repositories via /api/v1/github/repos/select first.",
        )

    analyses_results = []
    all_extracted_skills: dict[str, dict[str, Any]] = {}

    for repo in repositories:
        parts = repo.full_name.split("/")
        if len(parts) != 2:
            continue
        owner, repo_name = parts[0], parts[1]

        analyzer = RepositoryAnalyzer(repo_full_name=repo.full_name)

        # 1. Fetch languages breakdown
        languages = await client.get_repository_languages(owner, repo_name)
        analyzer.analyze_languages(languages)

        # 2. Fetch git tree to inspect structure
        tree = await client.get_repository_tree(owner, repo_name, repo.default_branch)
        analyzer.analyze_tree(tree)

        # 3. Target candidate dependency manifests and source files
        manifest_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
            "package.json",
            "go.mod",
            "Cargo.toml",
            "Dockerfile",
            "docker-compose.yml",
        ]

        file_tree_paths = [item.get("path", "") for item in tree]
        scanned_files = []

        for manifest_candidate in manifest_files:
            # Check if file exists in root or direct paths
            matching_paths = [p for p in file_tree_paths if p.lower().endswith(manifest_candidate.lower())]
            for m_path in matching_paths[:3]:  # Limit depth per candidate
                content = await client.get_file_content(owner, repo_name, m_path, repo.default_branch)
                if content:
                    analyzer.analyze_manifest_content(m_path, content)
                    scanned_files.append(m_path)

        # 4. Safely inspect a sample of Python files for imports (static AST)
        py_files = [p for p in file_tree_paths if p.endswith(".py") and "test" not in p.lower()][:5]
        for py_path in py_files:
            content = await client.get_file_content(owner, repo_name, py_path, repo.default_branch)
            if content:
                analyzer.analyze_source_code_imports(py_path, content)
                scanned_files.append(py_path)

        extracted = analyzer.get_results()

        # Update or create analysis record
        analysis_record = RepositoryAnalysis(
            firebase_uid=current_user.uid,
            repository_id=repo.id,
            repository_full_name=repo.full_name,
            status="completed",
            languages_breakdown=languages,
            extracted_skills=extracted,
            file_tree_summary={"total_files": len(tree), "scanned_files": scanned_files},
            completed_at=datetime.now(timezone.utc),
        )
        db.add(analysis_record)

        repo.last_analyzed_at = datetime.now(timezone.utc)
        analyses_results.append(analysis_record)

        # Merge extracted skills into user skill inventory
        for s in extracted:
            s_name = s["skill_name"]
            if s_name not in all_extracted_skills:
                all_extracted_skills[s_name] = {
                    "skill_name": s_name,
                    "category": s["category"],
                    "confidence_score": s["confidence_score"],
                    "evidence": s["evidence"],
                    "source_repositories": [repo.full_name],
                }
            else:
                # Merge evidence and increase confidence
                all_extracted_skills[s_name]["evidence"].extend(s["evidence"])
                if repo.full_name not in all_extracted_skills[s_name]["source_repositories"]:
                    all_extracted_skills[s_name]["source_repositories"].append(repo.full_name)
                # Boost confidence from multi-repo discovery
                cur = all_extracted_skills[s_name]["confidence_score"]
                all_extracted_skills[s_name]["confidence_score"] = min(0.99, cur + 0.05)

    # 5. Persist aggregated student skills in database
    for s_name, s_data in all_extracted_skills.items():
        stmt_skill = select(StudentSkill).where(
            StudentSkill.firebase_uid == current_user.uid,
            StudentSkill.skill_name == s_name,
        )
        existing_skill = (await db.execute(stmt_skill)).scalar_one_or_none()

        if existing_skill:
            existing_skill.confidence_score = s_data["confidence_score"]
            existing_skill.evidence = s_data["evidence"]
            existing_skill.source_repositories = s_data["source_repositories"]
        else:
            new_skill = StudentSkill(
                firebase_uid=current_user.uid,
                skill_name=s_name,
                category=s_data["category"],
                confidence_score=s_data["confidence_score"],
                evidence=s_data["evidence"],
                source_repositories=s_data["source_repositories"],
            )
            db.add(new_skill)

    # 6. Build and persist skill graph edges
    _, graph_edges = build_skill_graph(list(all_extracted_skills.values()))

    # Clear previous graph edges for this user to avoid stale duplicates
    await db.execute(delete(SkillGraphEdge).where(SkillGraphEdge.firebase_uid == current_user.uid))

    for edge in graph_edges:
        db.add(
            SkillGraphEdge(
                firebase_uid=current_user.uid,
                source_skill=edge["source"],
                target_skill=edge["target"],
                relationship_type=edge["relationship_type"],
                weight=edge["weight"],
            )
        )

    await db.commit()
    for ar in analyses_results:
        await db.refresh(ar)

    return GitHubAnalyzeResponse(
        message=f"Successfully analyzed {len(analyses_results)} repositories.",
        total_analyzed=len(analyses_results),
        analyses=[AnalysisResultItem.model_validate(ar) for ar in analyses_results],
    )


@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisResultItem,
    summary="Get Specific Analysis Details",
    description="Retrieve the results of a repository analysis with strict ownership verification.",
)
async def get_analysis_details(
    analysis_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryAnalysis:
    """Fetch analysis record verifying per-user isolation."""
    stmt = select(RepositoryAnalysis).where(
        RepositoryAnalysis.id == analysis_id,
        RepositoryAnalysis.firebase_uid == current_user.uid,
    )
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis not found.",
        )

    return analysis
