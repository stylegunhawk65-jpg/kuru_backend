"""Static code repository analyzer and skill graph builder (zero untrusted code execution)."""

import ast
import json
import logging
import re
from typing import Any

logger = logging.getLogger("kuru.analyzer")

# Predefined skill taxonomy and ecosystem relationships
SKILL_TAXONOMY: dict[str, dict[str, Any]] = {
    # Languages
    "Python": {"category": "Language", "related": []},
    "JavaScript": {"category": "Language", "related": []},
    "TypeScript": {"category": "Language", "related": [("JavaScript", "superset_of", 1.0)]},
    "Go": {"category": "Language", "related": []},
    "Rust": {"category": "Language", "related": []},
    "Java": {"category": "Language", "related": []},
    "Kotlin": {"category": "Language", "related": [("Java", "interoperable_with", 0.9)]},
    "C++": {"category": "Language", "related": []},
    "SQL": {"category": "Language", "related": []},
    "HTML/CSS": {"category": "Language", "related": []},

    # Python Frameworks & Libraries
    "FastAPI": {"category": "Framework", "related": [("Python", "requires_language", 1.0)]},
    "Django": {"category": "Framework", "related": [("Python", "requires_language", 1.0)]},
    "Flask": {"category": "Framework", "related": [("Python", "requires_language", 1.0)]},
    "SQLAlchemy": {"category": "Library", "related": [("Python", "requires_language", 1.0), ("SQL", "integrates_with", 0.9)]},
    "Pydantic": {"category": "Library", "related": [("Python", "requires_language", 1.0)]},
    "Celery": {"category": "Library", "related": [("Python", "requires_language", 1.0)]},
    "PyTorch": {"category": "Framework", "related": [("Python", "requires_language", 1.0)]},
    "TensorFlow": {"category": "Framework", "related": [("Python", "requires_language", 1.0)]},
    "Pandas": {"category": "Library", "related": [("Python", "requires_language", 1.0)]},
    "NumPy": {"category": "Library", "related": [("Python", "requires_language", 1.0)]},
    "Scikit-learn": {"category": "Library", "related": [("Python", "requires_language", 1.0)]},

    # JS/TS Frameworks & Libraries
    "React": {"category": "Framework", "related": [("JavaScript", "requires_language", 0.9), ("TypeScript", "integrates_with", 0.8)]},
    "Next.js": {"category": "Framework", "related": [("React", "built_on", 1.0)]},
    "Vue.js": {"category": "Framework", "related": [("JavaScript", "requires_language", 0.9)]},
    "Angular": {"category": "Framework", "related": [("TypeScript", "requires_language", 1.0)]},
    "Node.js": {"category": "Framework", "related": [("JavaScript", "requires_language", 1.0)]},
    "Express.js": {"category": "Framework", "related": [("Node.js", "built_on", 1.0)]},
    "NestJS": {"category": "Framework", "related": [("TypeScript", "requires_language", 1.0), ("Node.js", "built_on", 0.9)]},
    "Tailwind CSS": {"category": "Library", "related": [("HTML/CSS", "built_on", 0.9)]},
    "Redux": {"category": "Library", "related": [("React", "integrates_with", 0.9)]},

    # Java/Kotlin Ecosystem
    "Spring Boot": {"category": "Framework", "related": [("Java", "requires_language", 1.0)]},
    "Hibernate": {"category": "Library", "related": [("Java", "requires_language", 1.0), ("SQL", "integrates_with", 0.9)]},
    "Android": {"category": "Framework", "related": [("Kotlin", "requires_language", 0.9), ("Java", "requires_language", 0.8)]},

    # Go Ecosystem
    "Gin": {"category": "Framework", "related": [("Go", "requires_language", 1.0)]},
    "Fiber": {"category": "Framework", "related": [("Go", "requires_language", 1.0)]},
    "GORM": {"category": "Library", "related": [("Go", "requires_language", 1.0), ("SQL", "integrates_with", 0.9)]},

    # Rust Ecosystem
    "Actix-web": {"category": "Framework", "related": [("Rust", "requires_language", 1.0)]},
    "Tokio": {"category": "Library", "related": [("Rust", "requires_language", 1.0)]},
    "Axum": {"category": "Framework", "related": [("Rust", "requires_language", 1.0)]},

    # DevOps, Databases, Tools
    "Docker": {"category": "DevOps/Tool", "related": []},
    "Kubernetes": {"category": "DevOps/Tool", "related": [("Docker", "integrates_with", 0.9)]},
    "GitHub Actions": {"category": "DevOps/Tool", "related": []},
    "PostgreSQL": {"category": "Database", "related": [("SQL", "dialect_of", 1.0)]},
    "MongoDB": {"category": "Database", "related": []},
    "Redis": {"category": "Database", "related": []},
}

# Package name lookup mapping normalized package names to canonical skills
PACKAGE_TO_SKILL: dict[str, str] = {
    # Python
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "celery": "Celery",
    "torch": "PyTorch",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "TensorFlow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "psycopg": "PostgreSQL",
    "psycopg2": "PostgreSQL",
    "asyncpg": "PostgreSQL",
    "pymongo": "MongoDB",
    "redis": "Redis",

    # JavaScript / TypeScript
    "react": "React",
    "react-dom": "React",
    "next": "Next.js",
    "vue": "Vue.js",
    "@angular/core": "Angular",
    "express": "Express.js",
    "@nestjs/core": "NestJS",
    "tailwindcss": "Tailwind CSS",
    "redux": "Redux",
    "@reduxjs/toolkit": "Redux",
    "typescript": "TypeScript",
    "prisma": "PostgreSQL",
    "pg": "PostgreSQL",
    "mongodb": "MongoDB",
    "mongoose": "MongoDB",
    "ioredis": "Redis",

    # Java / Kotlin
    "spring-boot": "Spring Boot",
    "spring-boot-starter": "Spring Boot",
    "hibernate-core": "Hibernate",

    # Go
    "github.com/gin-gonic/gin": "Gin",
    "github.com/gofiber/fiber": "Fiber",
    "gorm.io/gorm": "GORM",

    # Rust
    "actix-web": "Actix-web",
    "tokio": "Tokio",
    "axum": "Axum",
}


def parse_requirements_txt(content: str) -> list[str]:
    """Extract package names from requirements.txt."""
    packages = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Extract package name before operators (==, >=, <=, ~=, <, >, ;)
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
        if match:
            packages.append(match.group(1).lower())
    return packages


def parse_pyproject_toml(content: str) -> list[str]:
    """Extract dependency names from pyproject.toml."""
    packages = []
    # Match strings inside dependencies = [...] or [project.dependencies]
    in_dependencies = False
    for line in content.splitlines():
        trimmed = line.strip()
        if "dependencies" in trimmed and "=" in trimmed:
            in_dependencies = True
        if in_dependencies:
            matches = re.findall(r'"([a-zA-Z0-9_\-\.]+)[^"]*"', trimmed)
            matches += re.findall(r"'([a-zA-Z0-9_\-\.]+)[^']*'", trimmed)
            for pkg in matches:
                if pkg not in ("project", "dependencies"):
                    packages.append(pkg.lower())
            if "]" in trimmed:
                in_dependencies = False
    return packages


def parse_package_json(content: str) -> list[str]:
    """Extract dependencies and devDependencies from package.json."""
    try:
        data = json.loads(content)
        deps = list(data.get("dependencies", {}).keys())
        dev_deps = list(data.get("devDependencies", {}).keys())
        return [pkg.lower() for pkg in deps + dev_deps]
    except Exception:
        return []


def parse_go_mod(content: str) -> list[str]:
    """Extract required packages from go.mod."""
    packages = []
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("require "):
            parts = trimmed.split()
            if len(parts) >= 2:
                packages.append(parts[1].lower())
        elif trimmed and not trimmed.startswith("module") and not trimmed.startswith("go "):
            parts = trimmed.split()
            if len(parts) >= 2 and "/" in parts[0]:
                packages.append(parts[0].lower())
    return packages


def parse_cargo_toml(content: str) -> list[str]:
    """Extract crate names from Cargo.toml."""
    crates = []
    in_deps = False
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("[dependencies]") or trimmed.startswith("[dev-dependencies]"):
            in_deps = True
            continue
        if trimmed.startswith("[") and in_deps:
            in_deps = False
        if in_deps and "=" in trimmed:
            crate_name = trimmed.split("=")[0].strip()
            crates.append(crate_name.lower())
    return crates


def parse_python_ast_imports(code: str) -> list[str]:
    """Safely parse Python AST to identify imported modules without executing code."""
    imports = []
    try:
        import textwrap
        tree = ast.parse(textwrap.dedent(code))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0].lower())
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0].lower())
    except Exception:
        pass
    return list(set(imports))


class RepositoryAnalyzer:
    """Performs evidence-backed static analysis on repository artifacts."""

    def __init__(self, repo_full_name: str):
        self.repo_full_name = repo_full_name
        self.extracted_skills: dict[str, dict[str, Any]] = {}

    def _add_evidence(
        self,
        skill_name: str,
        category: str,
        evidence_type: str,
        file_path: str,
        detail: str,
        base_confidence: float = 0.75,
    ) -> None:
        """Register skill evidence and update confidence score."""
        if skill_name not in self.extracted_skills:
            self.extracted_skills[skill_name] = {
                "skill_name": skill_name,
                "category": category,
                "confidence_score": base_confidence,
                "evidence": [],
            }
        else:
            # Boost confidence when multiple independent evidences are discovered
            current_score = self.extracted_skills[skill_name]["confidence_score"]
            self.extracted_skills[skill_name]["confidence_score"] = min(
                0.98, current_score + 0.10
            )

        self.extracted_skills[skill_name]["evidence"].append({
            "type": evidence_type,
            "repository": self.repo_full_name,
            "file_path": file_path,
            "detail": detail,
        })

    def analyze_languages(self, languages_breakdown: dict[str, int]) -> None:
        """Analyze repository language byte breakdown."""
        total_bytes = sum(languages_breakdown.values())
        if total_bytes <= 0:
            return

        for lang, byte_count in languages_breakdown.items():
            ratio = byte_count / total_bytes
            confidence = min(0.98, max(0.50, round(0.60 + (ratio * 0.35), 2)))
            category = SKILL_TAXONOMY.get(lang, {}).get("category", "Language")

            self._add_evidence(
                skill_name=lang,
                category=category,
                evidence_type="language_stats",
                file_path="languages_breakdown",
                detail=f"{lang} constitutes {round(ratio * 100, 1)}% of repository codebase ({byte_count} bytes)",
                base_confidence=confidence,
            )

    def analyze_tree(self, tree_items: list[dict[str, Any]]) -> None:
        """Analyze repository file paths for Docker, CI/CD, and infrastructure patterns."""
        for item in tree_items:
            path = item.get("path", "")
            lower_path = path.lower()

            if lower_path in ("dockerfile", "docker-compose.yml", "docker-compose.yaml"):
                self._add_evidence(
                    skill_name="Docker",
                    category="DevOps/Tool",
                    evidence_type="file_heuristic",
                    file_path=path,
                    detail=f"Detected containerization file: {path}",
                    base_confidence=0.85,
                )
            elif ".github/workflows" in lower_path and (lower_path.endswith(".yml") or lower_path.endswith(".yaml")):
                self._add_evidence(
                    skill_name="GitHub Actions",
                    category="DevOps/Tool",
                    evidence_type="file_heuristic",
                    file_path=path,
                    detail=f"Detected CI/CD workflow pipeline: {path}",
                    base_confidence=0.85,
                )
            elif "k8s" in lower_path or "kubernetes" in lower_path:
                self._add_evidence(
                    skill_name="Kubernetes",
                    category="DevOps/Tool",
                    evidence_type="file_heuristic",
                    file_path=path,
                    detail=f"Detected Kubernetes configuration: {path}",
                    base_confidence=0.80,
                )

    def analyze_manifest_content(self, file_path: str, content: str) -> None:
        """Parse dependency manifests safely."""
        lower_path = file_path.lower()
        packages: list[str] = []

        if lower_path.endswith("requirements.txt") or lower_path.endswith("requirements-dev.txt"):
            packages = parse_requirements_txt(content)
            self._add_evidence("Python", "Language", "manifest_dependency", file_path, "Python dependencies specified in requirements.txt", 0.85)
        elif lower_path.endswith("pyproject.toml"):
            packages = parse_pyproject_toml(content)
            self._add_evidence("Python", "Language", "manifest_dependency", file_path, "Python project manifest pyproject.toml", 0.85)
        elif lower_path.endswith("package.json"):
            packages = parse_package_json(content)
            self._add_evidence("JavaScript", "Language", "manifest_dependency", file_path, "JavaScript/Node.js package.json manifest", 0.80)
        elif lower_path.endswith("go.mod"):
            packages = parse_go_mod(content)
            self._add_evidence("Go", "Language", "manifest_dependency", file_path, "Go module declaration in go.mod", 0.90)
        elif lower_path.endswith("cargo.toml"):
            packages = parse_cargo_toml(content)
            self._add_evidence("Rust", "Language", "manifest_dependency", file_path, "Rust Cargo manifest in Cargo.toml", 0.90)
        elif lower_path.endswith("pubspec.yaml"):
            self._add_evidence("Flutter", "Framework", "manifest_dependency", file_path, "Flutter application manifest pubspec.yaml", 0.90)
            self._add_evidence("Dart", "Language", "manifest_dependency", file_path, "Dart SDK dependencies in pubspec.yaml", 0.90)
            if "riverpod" in content.lower():
                self._add_evidence("Riverpod", "Framework", "manifest_dependency", file_path, "Flutter Riverpod state management in pubspec.yaml", 0.85)
            if "firebase" in content.lower():
                self._add_evidence("Firebase", "Cloud", "manifest_dependency", file_path, "Firebase SDK integration in pubspec.yaml", 0.85)

        for pkg in packages:
            if pkg in PACKAGE_TO_SKILL:
                canonical_skill = PACKAGE_TO_SKILL[pkg]
                category = SKILL_TAXONOMY.get(canonical_skill, {}).get("category", "Framework")
                self._add_evidence(
                    skill_name=canonical_skill,
                    category=category,
                    evidence_type="manifest_dependency",
                    file_path=file_path,
                    detail=f"Declared dependency: {pkg}",
                    base_confidence=0.80,
                )

    def analyze_source_code_imports(self, file_path: str, content: str) -> None:
        """Safely inspect source file imports via AST."""
        if file_path.endswith(".py"):
            modules = parse_python_ast_imports(content)
            for mod in modules:
                if mod in PACKAGE_TO_SKILL:
                    canonical_skill = PACKAGE_TO_SKILL[mod]
                    category = SKILL_TAXONOMY.get(canonical_skill, {}).get("category", "Framework")
                    self._add_evidence(
                        skill_name=canonical_skill,
                        category=category,
                        evidence_type="source_import",
                        file_path=file_path,
                        detail=f"Source code import: {mod}",
                        base_confidence=0.75,
                    )

    def get_results(self) -> list[dict[str, Any]]:
        """Return list of all extracted skills sorted by confidence."""
        results = list(self.extracted_skills.values())
        results.sort(key=lambda s: s["confidence_score"], reverse=True)
        return results


def build_skill_graph(
    skills: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate graph nodes and relationship edges for a set of student skills."""
    skill_names = {s["skill_name"] for s in skills}
    nodes = []
    edges = []

    for s in skills:
        name = s["skill_name"]
        nodes.append({
            "id": name,
            "name": name,
            "category": s["category"],
            "confidence_score": s["confidence_score"],
            "evidence_count": len(s.get("evidence", [])),
            "repo_count": len(s.get("source_repositories", [])),
        })

        # Check known relationship definitions
        taxonomy_info = SKILL_TAXONOMY.get(name)
        if taxonomy_info:
            for target_skill, rel_type, weight in taxonomy_info.get("related", []):
                if target_skill in skill_names:
                    edges.append({
                        "source": name,
                        "target": target_skill,
                        "relationship_type": rel_type,
                        "weight": weight,
                    })

    return nodes, edges
