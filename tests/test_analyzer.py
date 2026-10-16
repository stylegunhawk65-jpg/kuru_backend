"""Unit tests for static manifest parsers, AST import extractor, and skill graph builder."""

from app.services.analyzer import (
    RepositoryAnalyzer,
    build_skill_graph,
    parse_cargo_toml,
    parse_go_mod,
    parse_package_json,
    parse_pyproject_toml,
    parse_python_ast_imports,
    parse_requirements_txt,
)


def test_parse_requirements_txt():
    """Ensure requirements.txt lines are parsed accurately with version specifiers stripped."""
    content = """
    # Core dependencies
    fastapi>=0.115.0
    uvicorn[standard]==0.24.0
    sqlalchemy>=2.0.0
    asyncpg<=0.30.0
    torch~=2.1.0
    --extra-index-url https://custom.repo.org/simple
    """
    pkgs = parse_requirements_txt(content)
    assert "fastapi" in pkgs
    assert "uvicorn" in pkgs
    assert "sqlalchemy" in pkgs
    assert "asyncpg" in pkgs
    assert "torch" in pkgs
    assert "--extra-index-url" not in pkgs


def test_parse_pyproject_toml():
    """Ensure pyproject.toml dependencies array is parsed."""
    content = """
    [project]
    name = "sample-app"
    dependencies = [
        "django>=5.0",
        "celery>=5.3",
        "redis>=4.0",
    ]
    """
    pkgs = parse_pyproject_toml(content)
    assert "django" in pkgs
    assert "celery" in pkgs
    assert "redis" in pkgs


def test_parse_package_json():
    """Ensure package.json dependencies and devDependencies are extracted."""
    content = """
    {
      "name": "frontend",
      "dependencies": {
        "react": "^18.2.0",
        "next": "14.0.0",
        "tailwindcss": "^3.3.0"
      },
      "devDependencies": {
        "typescript": "^5.0.0"
      }
    }
    """
    pkgs = parse_package_json(content)
    assert "react" in pkgs
    assert "next" in pkgs
    assert "tailwindcss" in pkgs
    assert "typescript" in pkgs


def test_parse_go_mod():
    """Ensure go.mod module requirements are extracted."""
    content = """
    module github.com/user/service

    go 1.22

    require (
        github.com/gin-gonic/gin v1.9.1
        gorm.io/gorm v1.25.7
    )
    """
    pkgs = parse_go_mod(content)
    assert "github.com/gin-gonic/gin" in pkgs
    assert "gorm.io/gorm" in pkgs


def test_parse_cargo_toml():
    """Ensure Cargo.toml dependencies are parsed."""
    content = """
    [package]
    name = "rust-service"
    version = "0.1.0"

    [dependencies]
    actix-web = "4"
    tokio = { version = "1", features = ["full"] }
    """
    crates = parse_cargo_toml(content)
    assert "actix-web" in crates
    assert "tokio" in crates


def test_parse_python_ast_imports():
    """Ensure static AST parsing extracts top-level module imports without executing code."""
    code = """
    import os
    import sys
    from fastapi import FastAPI, Depends
    import torch.nn as nn
    from sqlalchemy.orm import Session
    """
    imports = parse_python_ast_imports(code)
    assert "fastapi" in imports
    assert "torch" in imports
    assert "sqlalchemy" in imports


def test_confidence_score_multi_evidence_boost():
    """Ensure discovering multiple evidence sources boosts confidence score."""
    analyzer = RepositoryAnalyzer(repo_full_name="testuser/ai-service")

    # Add manifest evidence
    analyzer.analyze_manifest_content("requirements.txt", "fastapi>=0.115.0\npydantic>=2.0")
    initial_score = analyzer.extracted_skills["FastAPI"]["confidence_score"]

    # Add code import evidence (should increase confidence)
    analyzer.analyze_source_code_imports("main.py", "from fastapi import FastAPI\napp = FastAPI()")
    boosted_score = analyzer.extracted_skills["FastAPI"]["confidence_score"]

    assert boosted_score > initial_score
    assert len(analyzer.extracted_skills["FastAPI"]["evidence"]) == 2


def test_build_skill_graph_relationships():
    """Ensure skill graph identifies taxonomy relationships like FastAPI -> Python."""
    skills = [
        {"skill_name": "FastAPI", "category": "Framework", "confidence_score": 0.95, "evidence": ["e1"], "source_repositories": ["r1"]},
        {"skill_name": "Python", "category": "Language", "confidence_score": 0.98, "evidence": ["e2"], "source_repositories": ["r1"]},
        {"skill_name": "SQLAlchemy", "category": "Library", "confidence_score": 0.85, "evidence": ["e3"], "source_repositories": ["r1"]},
        {"skill_name": "SQL", "category": "Language", "confidence_score": 0.80, "evidence": ["e4"], "source_repositories": ["r1"]},
    ]

    nodes, edges = build_skill_graph(skills)
    assert len(nodes) == 4

    edge_pairs = [(e["source"], e["target"], e["relationship_type"]) for e in edges]
    assert ("FastAPI", "Python", "requires_language") in edge_pairs
    assert ("SQLAlchemy", "Python", "requires_language") in edge_pairs
    assert ("SQLAlchemy", "SQL", "integrates_with") in edge_pairs
