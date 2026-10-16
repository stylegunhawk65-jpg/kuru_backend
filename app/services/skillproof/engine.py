"""SkillProof Analysis Engine — Orchestrates repository skill extraction, code mapping, and similarity checking.

Adheres strictly to honesty guidelines:
- Never labels similarity as AI generation or proof of plagiarism.
- Explicitly handles missing references and coverage limitations.
- Enforces zero untrusted code execution.
"""

from datetime import datetime, timezone
import logging
from typing import Any

from app.services.github_client import GitHubClient
from app.services.skillproof.detector import (
    SkillDetectorAndMapper,
    detect_file_language,
    is_irrelevant_file,
)
from app.services.skillproof.reference_corpus import reference_registry
from app.services.skillproof.similarity import similarity_engine

logger = logging.getLogger("kuru.skillproof.engine")

STANDARD_HONEST_DISCLAIMER = (
    "Code similarity indicates structural, lexical, or syntactic overlap with canonical reference patterns, "
    "starter templates, or standard library idioms. High similarity to reference boilerplate is common and "
    "expected in standard framework usage and does NOT indicate plagiarism, lack of understanding, or "
    "AI generation. Similarity alone must never be used to judge student competency or employment eligibility."
)


class SkillProofEngine:
    """Core analysis engine for SkillProof verification runs."""

    @classmethod
    async def analyze_repository(
        cls,
        github_client: GitHubClient,
        owner: str,
        repo: str,
        default_branch: str = "main",
        selected_skills: list[str] | None = None,
        max_files_to_inspect: int = 25,
    ) -> dict[str, Any]:
        """Perform end-to-end SkillProof analysis on a GitHub repository.
        
        Zero untrusted code execution. Distinguishes dependency vs implementation evidence.
        """
        logger.info("Starting SkillProof analysis on %s/%s (selected: %s)", owner, repo, selected_skills)
        detector = SkillDetectorAndMapper()

        # 1. Fetch git tree
        tree_items = await github_client.get_repository_tree(owner, repo, branch=default_branch)
        if not tree_items:
            logger.warning("No tree items found for %s/%s", owner, repo)

        file_paths = [item.get("path", "") for item in tree_items if item.get("type") == "blob"]

        # 2. Scan Manifest Files First (Dependency Evidence)
        manifest_candidates = [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
            "package.json",
            "go.mod",
            "Cargo.toml",
        ]
        manifest_paths = [p for p in file_paths if any(p.lower().endswith(m) for m in manifest_candidates)]

        manifest_contents: dict[str, str] = {}
        for m_path in manifest_paths[:6]:
            content = await github_client.get_file_content(owner, repo, m_path, ref=default_branch)
            if content:
                manifest_contents[m_path] = content
                detector.scan_manifest(m_path, content)

        # 3. Identify and scan candidate source files (Implementation Evidence)
        candidate_source_paths = [
            p
            for p in file_paths
            if not is_irrelevant_file(p)
            and not any(p.lower().endswith(m) for m in manifest_candidates)
            and detect_file_language(p) != "Unknown"
        ]

        source_contents: dict[str, str] = {}
        scanned_count = 0

        # Prioritize core application files over test files
        sorted_sources = sorted(
            candidate_source_paths,
            key=lambda p: (1 if "test" in p.lower() else 0, len(p)),
        )

        for s_path in sorted_sources:
            if scanned_count >= max_files_to_inspect:
                break
            content = await github_client.get_file_content(owner, repo, s_path, ref=default_branch)
            if content:
                source_contents[s_path] = content
                detector.scan_source_file(s_path, content)
                scanned_count += 1

        # Also check for Dockerfile and Docker Compose
        docker_paths = [p for p in file_paths if "dockerfile" in p.lower() or "docker-compose" in p.lower()]
        for d_path in docker_paths[:3]:
            if d_path not in source_contents:
                content = await github_client.get_file_content(owner, repo, d_path, ref=default_branch)
                if content:
                    source_contents[d_path] = content
                    detector.scan_source_file(d_path, content)

        # 4. Aggregate detected skills and evaluate selection
        all_detected = detector.get_detected_skills()
        detected_skill_names = {s["skill_name"] for s in all_detected}

        # Filter by targeted skills if user specified them
        target_skills = [s.strip() for s in (selected_skills or []) if s.strip()]
        is_targeted = len(target_skills) > 0

        if is_targeted:
            active_skills = [s for s in all_detected if s["skill_name"].lower() in {t.lower() for t in target_skills}]
        else:
            active_skills = all_detected

        active_skill_names = {s["skill_name"] for s in active_skills}

        # 5. File-level Evidence and Similarity Evaluation
        file_evidence_records: list[dict[str, Any]] = []
        missing_references: list[dict[str, Any]] = []
        files_with_reference_sources = 0
        files_without_reference_sources = 0
        similarity_scores_collected: list[float] = []

        all_file_paths_analyzed = list(manifest_contents.keys()) + list(source_contents.keys())

        for f_path in all_file_paths_analyzed:
            content = manifest_contents.get(f_path) or source_contents.get(f_path) or ""
            lang = detect_file_language(f_path)

            # Determine skills relevant to this specific file
            skills_in_file: list[dict[str, Any]] = []
            for s in active_skills:
                if f_path in s["mapped_files"]:
                    skills_in_file.append({
                        "skill_name": s["skill_name"],
                        "category": s["category"],
                        "has_implementation": s["has_implementation_evidence"],
                        "has_dependency": s["has_dependency_evidence"],
                        "status": s["status"],
                    })

            # If user targeted specific skills, skip files that have no active targeted skills
            if is_targeted and not skills_in_file:
                continue

            has_implementation = any(s["has_implementation"] for s in skills_in_file)
            has_dependency = any(s["has_dependency"] for s in skills_in_file)

            # Similarity check against legitimate references
            similarity_findings: list[dict[str, Any]] = []
            has_ref_for_file = False

            for s in skills_in_file:
                s_name = s["skill_name"]
                if reference_registry.has_references_for_skill(s_name):
                    has_ref_for_file = True
                    matches = similarity_engine.compare_against_skill_references(content, s_name, lang)
                    similarity_findings.extend(matches)
                else:
                    # Note missing reference explicitly
                    if not any(m["skill"] == s_name for m in missing_references):
                        missing_references.append({
                            "skill": s_name,
                            "reason": f"No canonical reference corpus available for '{s_name}' in the registry. Code similarity was not evaluated.",
                        })

            if has_ref_for_file:
                files_with_reference_sources += 1
            else:
                files_without_reference_sources += 1

            # Track highest similarity score for file
            file_top_similarity = max([f["similarity_score"] for f in similarity_findings], default=0.0)
            if similarity_findings:
                similarity_scores_collected.append(file_top_similarity)

            file_evidence_records.append({
                "file_path": f_path,
                "language": lang,
                "has_implementation": has_implementation,
                "has_dependency": has_dependency,
                "skills_detected": skills_in_file,
                "similarity_findings": similarity_findings,
            })

        # 6. Compute Honest Summary & Metrics
        avg_similarity = (
            round(sum(similarity_scores_collected) / len(similarity_scores_collected), 4)
            if similarity_scores_collected
            else 0.0
        )
        total_scanned_files = len(file_evidence_records)
        ref_coverage_pct = (
            round((files_with_reference_sources / max(1, total_scanned_files)) * 100, 1)
            if total_scanned_files > 0
            else 0.0
        )

        implemented_count = sum(1 for s in active_skills if s["has_implementation_evidence"])
        dependency_only_count = sum(
            1 for s in active_skills if s["has_dependency_evidence"] and not s["has_implementation_evidence"]
        )

        summary = {
            "total_files_in_repository": len(tree_items),
            "total_files_scanned": total_scanned_files,
            "skills_detected_count": len(active_skills),
            "implemented_skills_count": implemented_count,
            "dependency_only_skills_count": dependency_only_count,
            "average_similarity_score": avg_similarity,
            "reference_coverage_percentage": ref_coverage_pct,
            "is_targeted_analysis": is_targeted,
            "target_skills": target_skills,
        }

        honest_reporting = {
            "plagiarism_claim": False,
            "ai_generation_claim": False,
            "disclaimer": STANDARD_HONEST_DISCLAIMER,
            "missing_references": missing_references,
            "coverage_scope": {
                "total_files_in_repo": len(tree_items),
                "files_scanned": total_scanned_files,
                "files_with_reference_sources": files_with_reference_sources,
                "files_without_reference_sources": files_without_reference_sources,
                "reference_coverage_percentage": ref_coverage_pct,
            },
        }

        return {
            "status": "completed",
            "summary": summary,
            "honest_reporting": honest_reporting,
            "detected_skills": active_skills,
            "evidence_records": file_evidence_records,
            "completed_at": datetime.now(timezone.utc),
        }


skillproof_engine = SkillProofEngine()
