"""Skill detection and skill-to-code mapping engine.

Strictly distinguishes dependency detection from actual implementation evidence.
Supports overlapping skills across source files and excludes irrelevant files.
Never executes code; uses AST and static analysis exclusively.
"""

import ast
import logging
import re
from typing import Any

from app.services.analyzer import (
    PACKAGE_TO_SKILL,
    SKILL_TAXONOMY,
    parse_cargo_toml,
    parse_go_mod,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
)

logger = logging.getLogger("kuru.skillproof.detector")

# Files or directories to ignore during skill-to-code mapping
EXCLUDED_PATTERNS = [
    ".git/",
    ".github/workflows",
    "node_modules/",
    "venv/",
    ".venv/",
    "__pycache__/",
    "dist/",
    "build/",
    ".min.js",
    ".min.css",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "cargo.lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
]

# Language mapping by file extension
EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".sql": "SQL",
    ".html": "HTML/CSS",
    ".css": "HTML/CSS",
    ".dockerfile": "Dockerfile",
    ".yml": "YAML",
    ".yaml": "YAML",
}


def is_irrelevant_file(file_path: str) -> bool:
    """Return True if the file should be excluded from code analysis."""
    low = file_path.lower()
    return any(pattern in low for pattern in EXCLUDED_PATTERNS)


def detect_file_language(file_path: str) -> str:
    """Detect programming language from file path."""
    low = file_path.lower()
    if low.endswith("dockerfile") or "dockerfile" in low:
        return "Dockerfile"
    for ext, lang in EXTENSION_TO_LANGUAGE.items():
        if low.endswith(ext):
            return lang
    return "Unknown"


class SkillDetectorAndMapper:
    """Detects skills across manifests and source code, mapping skills to source files."""

    def __init__(self) -> None:
        # Map: skill_name -> {category, dependency_evidence: [], implementation_evidence: [], mapped_files: set()}
        self._skills: dict[str, dict[str, Any]] = {}
        # Map: file_path -> list of skill findings
        self._file_skills: dict[str, list[dict[str, Any]]] = {}

    def _ensure_skill(self, skill_name: str, category: str | None = None) -> dict[str, Any]:
        """Ensure skill entry exists."""
        if skill_name not in self._skills:
            cat = category or SKILL_TAXONOMY.get(skill_name, {}).get("category", "Framework")
            self._skills[skill_name] = {
                "skill_name": skill_name,
                "category": cat,
                "confidence_score": 0.50,
                "dependency_evidence": [],
                "implementation_evidence": [],
                "mapped_files": set(),
            }
        return self._skills[skill_name]

    # -------------------------------------------------------------------------
    # Dependency Detection (Manifests)
    # -------------------------------------------------------------------------
    def scan_manifest(self, file_path: str, content: str) -> None:
        """Scan dependency manifests to register dependency evidence."""
        lower_path = file_path.lower()
        packages: list[str] = []

        if lower_path.endswith("requirements.txt") or lower_path.endswith("requirements-dev.txt"):
            packages = parse_requirements_txt(content)
            self._add_dependency_evidence("Python", "Language", file_path, "Python dependencies declared in requirements.txt", 1)
        elif lower_path.endswith("pyproject.toml"):
            packages = parse_pyproject_toml(content)
            self._add_dependency_evidence("Python", "Language", file_path, "Python project manifest pyproject.toml", 1)
        elif lower_path.endswith("package.json"):
            packages = parse_package_json(content)
            self._add_dependency_evidence("JavaScript", "Language", file_path, "Node.js package.json manifest", 1)
        elif lower_path.endswith("go.mod"):
            packages = parse_go_mod(content)
            self._add_dependency_evidence("Go", "Language", file_path, "Go module definition go.mod", 1)
        elif lower_path.endswith("cargo.toml"):
            packages = parse_cargo_toml(content)
            self._add_dependency_evidence("Rust", "Language", file_path, "Rust Cargo.toml manifest", 1)

        for pkg in packages:
            if pkg in PACKAGE_TO_SKILL:
                canonical = PACKAGE_TO_SKILL[pkg]
                category = SKILL_TAXONOMY.get(canonical, {}).get("category", "Framework")
                self._add_dependency_evidence(
                    skill_name=canonical,
                    category=category,
                    file_path=file_path,
                    detail=f"Declared dependency: '{pkg}'",
                )

    def _add_dependency_evidence(
        self,
        skill_name: str,
        category: str,
        file_path: str,
        detail: str,
        line_num: int | None = None,
    ) -> None:
        """Record dependency evidence."""
        entry = self._ensure_skill(skill_name, category)
        entry["dependency_evidence"].append({
            "type": "manifest_dependency",
            "file_path": file_path,
            "line_number": line_num,
            "detail": detail,
        })
        entry["mapped_files"].add(file_path)

    # -------------------------------------------------------------------------
    # Implementation Detection (Source Code)
    # -------------------------------------------------------------------------
    def scan_source_file(self, file_path: str, content: str) -> list[dict[str, Any]]:
        """Scan source code for concrete implementation evidence.
        
        Returns list of findings in this file.
        """
        if is_irrelevant_file(file_path):
            return []

        lang = detect_file_language(file_path)
        findings: list[dict[str, Any]] = []

        if lang == "Python":
            findings = self._scan_python_source(file_path, content)
        elif lang in ("JavaScript", "TypeScript"):
            findings = self._scan_js_ts_source(file_path, content, lang)
        elif lang == "Dockerfile":
            findings = self._scan_dockerfile(file_path, content)
        elif lang == "YAML":
            findings = self._scan_yaml_source(file_path, content)

        if findings:
            self._file_skills[file_path] = findings

        return findings

    def _scan_python_source(self, file_path: str, content: str) -> list[dict[str, Any]]:
        """Scan Python file using AST and regex for implementation evidence."""
        findings: list[dict[str, Any]] = []
        lines = content.splitlines()

        # Always register Python language implementation for non-empty .py file
        if len(lines) > 2:
            self._add_implementation_evidence(
                skill_name="Python",
                category="Language",
                file_path=file_path,
                line_start=1,
                line_end=min(10, len(lines)),
                code_snippet="\n".join(lines[:min(10, len(lines))]),
                detail="Python source code implementation",
            )
            findings.append({
                "skill": "Python",
                "category": "Language",
                "type": "source_implementation",
                "line_start": 1,
                "line_end": min(10, len(lines)),
            })

        # Try AST parsing
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                # Import statements
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_mod = alias.name.split(".")[0].lower()
                        if base_mod in PACKAGE_TO_SKILL:
                            skill = PACKAGE_TO_SKILL[base_mod]
                            l_start = getattr(node, "lineno", 1)
                            l_end = getattr(node, "end_lineno", l_start)
                            snippet = "\n".join(lines[l_start - 1 : l_end])
                            self._add_implementation_evidence(
                                skill_name=skill,
                                category=SKILL_TAXONOMY.get(skill, {}).get("category", "Framework"),
                                file_path=file_path,
                                line_start=l_start,
                                line_end=l_end,
                                code_snippet=snippet,
                                detail=f"Imports '{alias.name}' in source code",
                            )
                            findings.append({
                                "skill": skill,
                                "category": SKILL_TAXONOMY.get(skill, {}).get("category", "Framework"),
                                "type": "source_implementation",
                                "line_start": l_start,
                                "line_end": l_end,
                                "code_snippet": snippet,
                            })

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        base_mod = node.module.split(".")[0].lower()
                        if base_mod in PACKAGE_TO_SKILL:
                            skill = PACKAGE_TO_SKILL[base_mod]
                            l_start = getattr(node, "lineno", 1)
                            l_end = getattr(node, "end_lineno", l_start)
                            snippet = "\n".join(lines[l_start - 1 : l_end])
                            self._add_implementation_evidence(
                                skill_name=skill,
                                category=SKILL_TAXONOMY.get(skill, {}).get("category", "Framework"),
                                file_path=file_path,
                                line_start=l_start,
                                line_end=l_end,
                                code_snippet=snippet,
                                detail=f"Imports from '{node.module}' in source code",
                            )
                            findings.append({
                                "skill": skill,
                                "category": SKILL_TAXONOMY.get(skill, {}).get("category", "Framework"),
                                "type": "source_implementation",
                                "line_start": l_start,
                                "line_end": l_end,
                                "code_snippet": snippet,
                            })

                # Function decorators (e.g. FastAPI @router.get or Flask @app.route)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        dec_str = ""
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            dec_str = decorator.func.attr
                        elif isinstance(decorator, ast.Attribute):
                            dec_str = decorator.attr

                        if dec_str in ("get", "post", "put", "delete", "patch", "route"):
                            # Indicates Web API Framework implementation
                            l_start = getattr(node, "lineno", 1)
                            l_end = min(len(lines), l_start + 6)
                            snippet = "\n".join(lines[l_start - 1 : l_end])
                            for active_skill in ("FastAPI", "Flask"):
                                if active_skill in self._skills:
                                    self._add_implementation_evidence(
                                        skill_name=active_skill,
                                        category="Framework",
                                        file_path=file_path,
                                        line_start=l_start,
                                        line_end=l_end,
                                        code_snippet=snippet,
                                        detail=f"Route handler decorator '@{dec_str}' implemented",
                                    )

                # Class definitions (e.g. SQLAlchemy Base models or Pydantic BaseModel)
                elif isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        base_id = ""
                        if isinstance(base, ast.Name):
                            base_id = base.id
                        elif isinstance(base, ast.Attribute):
                            base_id = base.attr

                        if base_id in ("BaseModel", "Schema"):
                            l_start = getattr(node, "lineno", 1)
                            l_end = min(len(lines), l_start + 8)
                            snippet = "\n".join(lines[l_start - 1 : l_end])
                            self._add_implementation_evidence(
                                skill_name="Pydantic",
                                category="Library",
                                file_path=file_path,
                                line_start=l_start,
                                line_end=l_end,
                                code_snippet=snippet,
                                detail=f"Subclasses Pydantic '{base_id}' for data validation",
                            )
                        elif base_id in ("Base", "DeclarativeBase", "Model"):
                            l_start = getattr(node, "lineno", 1)
                            l_end = min(len(lines), l_start + 8)
                            snippet = "\n".join(lines[l_start - 1 : l_end])
                            self._add_implementation_evidence(
                                skill_name="SQLAlchemy",
                                category="Library",
                                file_path=file_path,
                                line_start=l_start,
                                line_end=l_end,
                                code_snippet=snippet,
                                detail=f"Defines database entity extending ORM '{base_id}'",
                            )

        except Exception as exc:
            logger.debug("AST parsing skipped for %s: %s", file_path, exc)

        return findings

    def _scan_js_ts_source(self, file_path: str, content: str, language: str) -> list[dict[str, Any]]:
        """Scan JavaScript or TypeScript source for React, Express, Vue, etc."""
        findings: list[dict[str, Any]] = []
        lines = content.splitlines()

        # Register language
        self._add_implementation_evidence(
            skill_name=language,
            category="Language",
            file_path=file_path,
            line_start=1,
            line_end=min(10, len(lines)),
            code_snippet="\n".join(lines[:min(10, len(lines))]),
            detail=f"{language} implementation file",
        )

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()

            # React imports / hooks
            if "from 'react'" in trimmed or 'from "react"' in trimmed or "useState" in trimmed or "useEffect" in trimmed:
                snippet = "\n".join(lines[max(0, idx - 1) : min(len(lines), idx + 4)])
                self._add_implementation_evidence(
                    skill_name="React",
                    category="Framework",
                    file_path=file_path,
                    line_start=idx,
                    line_end=min(len(lines), idx + 4),
                    code_snippet=snippet,
                    detail="React hooks / component declaration",
                )
                findings.append({"skill": "React", "line": idx})

            # Express imports / app setup
            if "express()" in trimmed or "require('express')" in trimmed or 'from "express"' in trimmed:
                snippet = "\n".join(lines[max(0, idx - 1) : min(len(lines), idx + 4)])
                self._add_implementation_evidence(
                    skill_name="Express.js",
                    category="Framework",
                    file_path=file_path,
                    line_start=idx,
                    line_end=min(len(lines), idx + 4),
                    code_snippet=snippet,
                    detail="Express server instantiation or route definition",
                )
                findings.append({"skill": "Express.js", "line": idx})

        return findings

    def _scan_dockerfile(self, file_path: str, content: str) -> list[dict[str, Any]]:
        """Scan Dockerfile for Docker skill evidence."""
        lines = content.splitlines()
        snippet = "\n".join(lines[:min(12, len(lines))])
        self._add_implementation_evidence(
            skill_name="Docker",
            category="DevOps/Tool",
            file_path=file_path,
            line_start=1,
            line_end=min(12, len(lines)),
            code_snippet=snippet,
            detail="Container image build configuration",
        )
        return [{"skill": "Docker", "line_start": 1, "line_end": min(12, len(lines))}]

    def _scan_yaml_source(self, file_path: str, content: str) -> list[dict[str, Any]]:
        """Scan YAML files for GitHub Actions or Docker Compose evidence."""
        low = file_path.lower()
        lines = content.splitlines()
        snippet = "\n".join(lines[:min(12, len(lines))])

        if ".github/workflows" in low or "action" in low:
            self._add_implementation_evidence(
                skill_name="GitHub Actions",
                category="DevOps/Tool",
                file_path=file_path,
                line_start=1,
                line_end=min(12, len(lines)),
                code_snippet=snippet,
                detail="CI/CD automated workflow configuration",
            )
            return [{"skill": "GitHub Actions", "line_start": 1, "line_end": min(12, len(lines))}]
        elif "docker-compose" in low:
            self._add_implementation_evidence(
                skill_name="Docker",
                category="DevOps/Tool",
                file_path=file_path,
                line_start=1,
                line_end=min(12, len(lines)),
                code_snippet=snippet,
                detail="Multi-container Docker Compose definition",
            )
            return [{"skill": "Docker", "line_start": 1, "line_end": min(12, len(lines))}]
        return []

    def _add_implementation_evidence(
        self,
        skill_name: str,
        category: str,
        file_path: str,
        line_start: int,
        line_end: int,
        code_snippet: str,
        detail: str,
    ) -> None:
        """Record concrete implementation evidence."""
        entry = self._ensure_skill(skill_name, category)
        entry["implementation_evidence"].append({
            "type": "source_implementation",
            "file_path": file_path,
            "line_start": line_start,
            "line_end": line_end,
            "code_snippet": code_snippet,
            "detail": detail,
        })
        entry["mapped_files"].add(file_path)

    # -------------------------------------------------------------------------
    # Aggregation & Status Determination
    # -------------------------------------------------------------------------
    def get_detected_skills(self) -> list[dict[str, Any]]:
        """Aggregate detected skills, distinguishing dependency vs implementation."""
        results: list[dict[str, Any]] = []

        for name, data in self._skills.items():
            dep_count = len(data["dependency_evidence"])
            imp_count = len(data["implementation_evidence"])

            has_dep = dep_count > 0
            has_imp = imp_count > 0

            if has_dep and has_imp:
                status = "implemented"
                confidence = min(0.99, 0.70 + (imp_count * 0.05) + (dep_count * 0.04))
            elif has_imp:
                status = "implementation_only"
                confidence = min(0.95, 0.65 + (imp_count * 0.06))
            elif has_dep:
                status = "dependency_only"
                confidence = min(0.80, 0.50 + (dep_count * 0.05))
            else:
                continue

            results.append({
                "skill_name": name,
                "category": data["category"],
                "confidence_score": round(confidence, 2),
                "has_dependency_evidence": has_dep,
                "has_implementation_evidence": has_imp,
                "status": status,
                "dependency_evidence_count": dep_count,
                "implementation_evidence_count": imp_count,
                "mapped_files": sorted(list(data["mapped_files"])),
                "evidence": data["implementation_evidence"] + data["dependency_evidence"],
            })

        # Sort by implementation status and confidence descending
        results.sort(
            key=lambda x: (
                1 if x["has_implementation_evidence"] else 0,
                x["confidence_score"],
            ),
            reverse=True,
        )
        return results

    def get_file_skills(self) -> dict[str, list[dict[str, Any]]]:
        """Return file-to-skills mapping."""
        return self._file_skills
