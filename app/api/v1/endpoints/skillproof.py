"""Authenticated SkillProof Engine endpoints: skill detection, code mapping, and honest similarity verification."""

from datetime import datetime, timezone
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.github import get_decrypted_github_token
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.github import GithubRepository
from app.models.skillproof import SkillProofEvidence, SkillProofRun
from app.schemas.skillproof import (
    DetectedSkillItem,
    SkillProofAnalyzeRequest,
    SkillProofDetectResponse,
    SkillProofEvidenceItem,
    SkillProofHonestReporting,
    SkillProofRepoItem,
    SkillProofRunListItem,
    SkillProofRunResponse,
)
from app.services.github_client import GitHubAPIError, GitHubClient
from app.services.skillproof.detector import SkillDetectorAndMapper
from app.services.skillproof.engine import skillproof_engine

logger = logging.getLogger("kuru.api.skillproof")
router = APIRouter()


async def _resolve_repo_details(
    repo_identifier: str,
    current_user: AuthenticatedUser,
    client: GitHubClient,
    db: AsyncSession,
) -> tuple[str, str, str, str]:
    """Resolve owner, repo_name, full_name, and default_branch from repo ID or full_name."""
    # 1. Check local GithubRepository records
    stmt = select(GithubRepository).where(
        GithubRepository.firebase_uid == current_user.uid,
    )
    if repo_identifier.isdigit():
        stmt = stmt.where(GithubRepository.github_repo_id == repo_identifier)
    elif "/" in repo_identifier:
        stmt = stmt.where(GithubRepository.full_name == repo_identifier)
    else:
        stmt = stmt.where(
            (GithubRepository.id == repo_identifier)
            | (GithubRepository.name == repo_identifier)
        )

    local_repo = (await db.execute(stmt)).scalar_one_or_none()
    if local_repo:
        parts = local_repo.full_name.split("/")
        return parts[0], parts[1], local_repo.full_name, local_repo.default_branch

    # 2. If "/" in identifier, fetch directly from GitHub
    if "/" in repo_identifier:
        parts = repo_identifier.strip().split("/")
        if len(parts) == 2:
            try:
                res = await client._request("GET", f"/repos/{parts[0]}/{parts[1]}")
                if res.status_code == 200:
                    data = res.json()
                    return parts[0], parts[1], data.get("full_name", repo_identifier), data.get("default_branch", "main")
            except Exception:
                pass

    # 3. Search user's repositories
    all_repos = await client.list_repositories(page=1, per_page=100)
    for r in all_repos:
        if str(r.get("id")) == repo_identifier or r.get("full_name") == repo_identifier or r.get("name") == repo_identifier:
            full = r.get("full_name", "")
            p = full.split("/")
            return p[0], p[1], full, r.get("default_branch", "main")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Repository '{repo_identifier}' not found or not accessible with connected GitHub account.",
    )


@router.get(
    "/repos",
    response_model=list[SkillProofRepoItem],
    summary="List Repositories for SkillProof",
    description="List connected user repositories annotated with past SkillProof analysis runs.",
)
async def list_skillproof_repositories(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkillProofRepoItem]:
    """Retrieve user repositories from database and GitHub with SkillProof metadata."""
    token = await get_decrypted_github_token(current_user, db)
    client = GitHubClient(token=token)
    gh_repos = await client.list_repositories(page=1, per_page=50)

    # Get local tracking records
    stmt_repos = select(GithubRepository).where(GithubRepository.firebase_uid == current_user.uid)
    local_repos = {r.github_repo_id: r for r in (await db.execute(stmt_repos)).scalars().all()}

    # Get run counts per repository
    stmt_counts = (
        select(SkillProofRun.repository_id, func.count(SkillProofRun.id).label("count"))
        .where(SkillProofRun.firebase_uid == current_user.uid)
        .group_by(SkillProofRun.repository_id)
    )
    counts_result = await db.execute(stmt_counts)
    run_counts = {str(row[0]): row[1] for row in counts_result.all()}

    items: list[SkillProofRepoItem] = []
    for r in gh_repos:
        r_id = str(r.get("id"))
        tracked = local_repos.get(r_id)
        items.append(
            SkillProofRepoItem(
                github_repo_id=r_id,
                name=r.get("name", ""),
                full_name=r.get("full_name", ""),
                default_branch=r.get("default_branch", "main"),
                primary_language=r.get("language"),
                is_private=r.get("private", False),
                description=r.get("description"),
                html_url=r.get("html_url", ""),
                last_analyzed_at=tracked.last_analyzed_at if tracked else None,
                skillproof_run_count=run_counts.get(r_id, 0),
            )
        )

    return items


@router.get(
    "/repos/{repo_id:path}/skills",
    response_model=SkillProofDetectResponse,
    summary="Detect Skills in Repository",
    description="Inspect repository manifests and source code; distinguish dependency evidence from implementation evidence.",
)
async def detect_repository_skills(
    repo_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillProofDetectResponse:
    """Detect skills in repository and classify as dependency_only, implementation_only, or implemented."""
    token = await get_decrypted_github_token(current_user, db)
    client = GitHubClient(token=token)

    owner, repo_name, full_name, default_branch = await _resolve_repo_details(repo_id, current_user, client, db)
    detector = SkillDetectorAndMapper()

    # Fetch tree
    tree = await client.get_repository_tree(owner, repo_name, branch=default_branch)
    file_paths = [item.get("path", "") for item in tree if item.get("type") == "blob"]

    # Scan manifests
    manifest_candidates = [
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "Cargo.toml",
    ]
    manifest_paths = [p for p in file_paths if any(p.lower().endswith(m) for m in manifest_candidates)]

    for m_path in manifest_paths[:6]:
        content = await client.get_file_content(owner, repo_name, m_path, ref=default_branch)
        if content:
            detector.scan_manifest(m_path, content)

    # Scan a sample of core source files
    source_candidates = [
        p
        for p in file_paths
        if p.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", "Dockerfile"))
        and "test" not in p.lower()
    ]
    for s_path in source_candidates[:15]:
        content = await client.get_file_content(owner, repo_name, s_path, ref=default_branch)
        if content:
            detector.scan_source_file(s_path, content)

    detected = detector.get_detected_skills()
    imp_count = sum(1 for s in detected if s["has_implementation_evidence"])
    dep_only_count = sum(1 for s in detected if s["has_dependency_evidence"] and not s["has_implementation_evidence"])

    return SkillProofDetectResponse(
        repository_full_name=full_name,
        default_branch=default_branch,
        skills_count=len(detected),
        implemented_count=imp_count,
        dependency_only_count=dep_only_count,
        skills=[DetectedSkillItem.model_validate(s) for s in detected],
    )


@router.post(
    "/analyze",
    response_model=SkillProofRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Targeted or Full SkillProof Analysis",
    description="Analyze repository code for selected skills or full repository. Evaluates multi-modal similarity against legitimate reference sources and generates honest reports.",
)
async def analyze_skillproof(
    payload: SkillProofAnalyzeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillProofRunResponse:
    """Execute SkillProof analysis, store run and file-level evidence in PostgreSQL, and return report."""
    token = await get_decrypted_github_token(current_user, db)
    client = GitHubClient(token=token)

    owner, repo_name, full_name, default_branch = await _resolve_repo_details(payload.repo_id, current_user, client, db)

    # Execute engine
    try:
        analysis_result = await skillproof_engine.analyze_repository(
            github_client=client,
            owner=owner,
            repo=repo_name,
            default_branch=default_branch,
            selected_skills=payload.selected_skills,
            max_files_to_inspect=payload.max_files,
        )
    except Exception as exc:
        logger.error("SkillProof engine analysis failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SkillProof analysis encountered an unexpected error: {str(exc)}",
        )

    # Persist SkillProofRun
    run = SkillProofRun(
        firebase_uid=current_user.uid,
        repository_id=payload.repo_id,
        repository_full_name=full_name,
        target_skills=payload.selected_skills or [],
        status=analysis_result["status"],
        summary=analysis_result["summary"],
        honest_reporting=analysis_result["honest_reporting"],
        completed_at=analysis_result["completed_at"],
    )
    db.add(run)
    await db.flush()  # Generate run.id

    # Persist file-level evidence records
    for rec in analysis_result["evidence_records"]:
        evidence = SkillProofEvidence(
            run_id=run.id,
            firebase_uid=current_user.uid,
            file_path=rec["file_path"],
            language=rec["language"],
            has_implementation=rec["has_implementation"],
            has_dependency=rec["has_dependency"],
            skills_detected=rec["skills_detected"],
            similarity_findings=rec["similarity_findings"],
        )
        db.add(evidence)

    await db.commit()
    await db.refresh(run)

    # Load with relationship
    stmt = (
        select(SkillProofRun)
        .options(selectinload(SkillProofRun.evidence_records))
        .where(SkillProofRun.id == run.id)
    )
    refreshed_run = (await db.execute(stmt)).scalar_one()

    return SkillProofRunResponse(
        id=refreshed_run.id,
        firebase_uid=refreshed_run.firebase_uid,
        repository_id=refreshed_run.repository_id,
        repository_full_name=refreshed_run.repository_full_name,
        status=refreshed_run.status,
        target_skills=refreshed_run.target_skills,
        summary=refreshed_run.summary,
        honest_reporting=SkillProofHonestReporting.model_validate(refreshed_run.honest_reporting),
        evidence_records=[
            SkillProofEvidenceItem(
                file_path=e.file_path,
                language=e.language,
                has_implementation=e.has_implementation,
                has_dependency=e.has_dependency,
                skills_detected=e.skills_detected,
                similarity_findings=e.similarity_findings,
            )
            for e in refreshed_run.evidence_records
        ],
        error_message=refreshed_run.error_message,
        created_at=refreshed_run.created_at,
        completed_at=refreshed_run.completed_at,
    )


@router.get(
    "/runs",
    response_model=list[SkillProofRunListItem],
    summary="List SkillProof Runs",
    description="List all past SkillProof runs for the authenticated user.",
)
async def list_skillproof_runs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkillProofRunListItem]:
    """Retrieve past SkillProof runs with strict user isolation."""
    offset = (page - 1) * per_page
    stmt = (
        select(SkillProofRun)
        .where(SkillProofRun.firebase_uid == current_user.uid)
        .order_by(SkillProofRun.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    runs = (await db.execute(stmt)).scalars().all()

    items = []
    for r in runs:
        summary = r.summary or {}
        items.append(
            SkillProofRunListItem(
                id=r.id,
                repository_id=r.repository_id,
                repository_full_name=r.repository_full_name,
                status=r.status,
                target_skills=r.target_skills,
                skills_detected_count=summary.get("skills_detected_count", len(r.target_skills)),
                average_similarity_score=summary.get("average_similarity_score", 0.0),
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
        )
    return items


@router.get(
    "/runs/{run_id}",
    response_model=SkillProofRunResponse,
    summary="Get SkillProof Run Details",
    description="Retrieve complete SkillProof report with evidence and honest reporting.",
)
async def get_skillproof_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkillProofRunResponse:
    """Retrieve run details enforcing strict per-user authorization."""
    stmt = (
        select(SkillProofRun)
        .options(selectinload(SkillProofRun.evidence_records))
        .where(
            SkillProofRun.id == run_id,
            SkillProofRun.firebase_uid == current_user.uid,
        )
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SkillProof run '{run_id}' not found.",
        )

    return SkillProofRunResponse(
        id=run.id,
        firebase_uid=run.firebase_uid,
        repository_id=run.repository_id,
        repository_full_name=run.repository_full_name,
        status=run.status,
        target_skills=run.target_skills,
        summary=run.summary,
        honest_reporting=SkillProofHonestReporting.model_validate(run.honest_reporting),
        evidence_records=[
            SkillProofEvidenceItem(
                file_path=e.file_path,
                language=e.language,
                has_implementation=e.has_implementation,
                has_dependency=e.has_dependency,
                skills_detected=e.skills_detected,
                similarity_findings=e.similarity_findings,
            )
            for e in run.evidence_records
        ],
        error_message=run.error_message,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


@router.delete(
    "/runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete SkillProof Run",
    description="Delete a SkillProof run and its associated evidence records.",
)
async def delete_skillproof_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete run enforcing strict user isolation."""
    stmt = select(SkillProofRun).where(
        SkillProofRun.id == run_id,
        SkillProofRun.firebase_uid == current_user.uid,
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SkillProof run '{run_id}' not found.",
        )

    await db.delete(run)
    await db.commit()
