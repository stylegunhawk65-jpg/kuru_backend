"""Tests for Phase 9 SkillProof Practical Assessment Engine:
Adaptive level selection, Qwen challenge generation, secure sandbox isolation,
timeouts, security scanning, hidden tests, authentication, cross-user isolation,
and Career Twin integration.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import AssessmentSubmission, PracticalAssessment
from app.models.profile import StudentProfile
from app.models.skill import StudentSkill
from app.models.skillproof import SkillProofRun
from app.services.assessments.evaluator import assessment_evaluator
from app.services.assessments.generator import (
    AdaptiveLevelSelector,
    PracticalChallengeGenerator,
    challenge_generator,
    level_selector,
)
from app.services.assessments.sandbox import (
    IsolatedExecutionSandbox,
    TestCase,
    sandbox_runner,
    scan_code_security,
)
from app.services.assessments.service import assessment_service


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
    """Mock Firebase authentication for assessment tests."""
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_token):
        yield


USER_A_HEADERS = {"Authorization": "Bearer token_user_a"}
USER_B_HEADERS = {"Authorization": "Bearer token_user_b"}


# -----------------------------------------------------------------------------
# 1. Unit Tests: Static Security Scanner & Sandbox Isolation
# -----------------------------------------------------------------------------
def test_security_scanner_blocks_malicious_operations():
    """Verify static AST scanner rejects dangerous modules, calls, and imports before execution."""
    malicious_scripts = [
        "import os\nos.system('whoami')",
        "import sys\nsys.exit(0)",
        "import subprocess\nsubprocess.run(['dir'])",
        "import socket\ns = socket.socket()",
        "from shutil import rmtree\nrmtree('/')",
        "eval('2 + 2')",
        "exec('print(1)')",
        "getattr(__import__('os'), 'system')('id')",
    ]

    for script in malicious_scripts:
        violations = scan_code_security(script)
        assert len(violations) > 0, f"Expected security violation for: {script}"


def test_security_scanner_allows_safe_code():
    """Verify safe functional code passes security inspection without false positives."""
    safe_script = """
def sanitize_params(data: dict) -> dict:
    result = {}
    for k, v in data.items():
        if v is not None and str(v).strip():
            result[k] = str(v).strip()
    return result
"""
    violations = scan_code_security(safe_script)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_sandbox_executes_valid_code_successfully():
    """Verify valid code runs in isolated subprocess and produces correct test results."""
    code = """
def add_numbers(a, b):
    return a + b
"""
    test_cases = [
        TestCase(name="test_positive", function_name="add_numbers", args=[2, 3], expected=5, is_hidden=False),
        TestCase(name="test_negative", function_name="add_numbers", args=[-1, 1], expected=0, is_hidden=True),
    ]

    res = await sandbox_runner.execute(submitted_code=code, test_cases=test_cases)
    assert res.status == "passed"
    assert len(res.test_results) == 2
    assert all(t.passed for t in res.test_results)
    assert res.isolation_guarantees.get("subprocess_isolated") is True


@pytest.mark.asyncio
async def test_sandbox_kills_infinite_loops_on_timeout():
    """Verify infinite loop submissions are forcefully killed on timeout."""
    infinite_loop_code = """
def stall(x):
    while True:
        pass
    return x
"""
    test_cases = [
        TestCase(name="test_stall", function_name="stall", args=[1], expected=1, is_hidden=False),
    ]

    short_timeout_sandbox = IsolatedExecutionSandbox(timeout_seconds=0.8)
    res = await short_timeout_sandbox.execute(submitted_code=infinite_loop_code, test_cases=test_cases)
    assert res.status == "timeout"
    assert "strict timeout" in res.error_message


@pytest.mark.asyncio
async def test_sandbox_blocks_unauthorized_imports_at_runtime():
    """Verify security violations halt execution before spawning subprocess."""
    hack_code = """
import os
def exploit():
    return os.listdir('.')
"""
    test_cases = [
        TestCase(name="test_hack", function_name="exploit", args=[], expected=[], is_hidden=False),
    ]

    res = await sandbox_runner.execute(submitted_code=hack_code, test_cases=test_cases)
    assert res.status == "security_violation"
    assert "Importing module 'os' is prohibited" in res.error_message


@pytest.mark.asyncio
async def test_sandbox_disabled_fallback_returns_disabled_status():
    """Verify that when sandbox is disabled, execution is rejected cleanly rather than running unsafely."""
    disabled_sandbox = IsolatedExecutionSandbox(enabled=False)
    res = await disabled_sandbox.execute(
        submitted_code="def f(): return 1",
        test_cases=[],
    )
    assert res.status == "execution_disabled"
    assert "disabled" in res.error_message


# -----------------------------------------------------------------------------
# 2. Unit Tests: Adaptive Level Selector & Challenge Generator
# -----------------------------------------------------------------------------
def test_adaptive_level_selection_rules():
    """Verify adaptive level selection grounds in target roles and similarity findings."""
    selector = AdaptiveLevelSelector()

    # Rule 1: Senior target role -> Advanced level
    senior_profile = StudentProfile(
        firebase_uid="usr_alpha",
        full_name="Lead Candidate",
        email="lead@kuru.ai",
        target_roles=["Senior Backend Architect", "Lead Engineer"],
    )
    lvl, c_type, rat = selector.select_level(skill_name="FastAPI", profile=senior_profile)
    assert lvl == "advanced"
    assert c_type == "transfer"
    assert "Senior" in rat or "target roles" in rat

    # Rule 2: High boilerplate similarity (>= 0.55) -> Intermediate Debugging
    high_sim_run = SkillProofRun(
        firebase_uid="usr_alpha",
        repository_id="repo1",
        repository_full_name="test/repo",
        target_skills=["FastAPI"],
        summary={"average_similarity_score": 0.68},
        honest_reporting={},
    )
    lvl, c_type, rat = selector.select_level(
        skill_name="FastAPI",
        skillproof_run=high_sim_run,
    )
    assert lvl == "intermediate"
    assert c_type == "debugging"
    assert "template alignment" in rat

    # Rule 3: Nascent skill evidence -> Basic level
    lvl, c_type, rat = selector.select_level(skill_name="Docker")
    assert lvl == "basic"
    assert c_type == "coding"


@pytest.mark.asyncio
async def test_challenge_generator_produces_structured_output():
    """Verify generator produces valid challenges with starter code and public/hidden tests."""
    gen = PracticalChallengeGenerator()
    challenge = await gen.generate_challenge(
        skill_name="FastAPI",
        level="intermediate",
        challenge_type="debugging",
    )

    assert "title" in challenge
    assert "starter_code" in challenge
    assert "entry_function" in challenge
    assert len(challenge["public_tests"]) > 0
    assert len(challenge["hidden_tests"]) > 0
    assert all(t["is_hidden"] is False for t in challenge["public_tests"])
    assert all(t["is_hidden"] is True for t in challenge["hidden_tests"])


@pytest.mark.asyncio
async def test_challenge_generator_fallback_on_model_failure():
    """Verify generator falls back gracefully to curated template if provider raises error."""
    broken_provider = AsyncMock()
    broken_provider.generate_structured.side_effect = RuntimeError("Simulated LLM API failure")

    gen = PracticalChallengeGenerator()
    challenge = await gen.generate_challenge(
        skill_name="FastAPI",
        level="basic",
        challenge_type="coding",
        provider=broken_provider,
    )

    # Must return valid curated fallback template rather than crashing
    assert "FastAPI" in challenge["title"]
    assert len(challenge["public_tests"]) > 0
    assert len(challenge["hidden_tests"]) > 0


# -----------------------------------------------------------------------------
# 3. Endpoint Tests: Authentication, Authorization & Hidden Test Shielding
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(async_client: AsyncClient):
    """Ensure all assessment endpoints return 401 Unauthorized when missing token."""
    endpoints = [
        ("POST", "/api/v1/assessments", {"skill_name": "FastAPI"}),
        ("GET", "/api/v1/assessments/test-id/challenge", None),
        ("POST", "/api/v1/assessments/test-id/submit", {"submitted_code": "pass"}),
        ("GET", "/api/v1/assessments/test-id/results", None),
        ("POST", "/api/v1/assessments/test-id/reassess", None),
        ("GET", "/api/v1/assessments", None),
        ("DELETE", "/api/v1/assessments/test-id", None),
    ]

    for method, path, payload in endpoints:
        if method == "POST":
            res = await async_client.post(path, json=payload or {})
        elif method == "GET":
            res = await async_client.get(path)
        elif method == "DELETE":
            res = await async_client.delete(path)

        assert res.status_code == 401, f"{method} {path} should return 401"
        assert "Authentication required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_create_and_retrieve_challenge_shields_hidden_tests(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Ensure GET /challenge returns challenge specifications but NEVER leaks hidden tests."""
    create_res = await async_client.post(
        "/api/v1/assessments",
        headers=USER_A_HEADERS,
        json={"skill_name": "FastAPI", "forced_level": "basic"},
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assessment_id = data["assessment_id"]

    # Challenge in response must have public tests but NO hidden tests field
    challenge = data["challenge"]
    assert "public_tests" in challenge
    assert "hidden_tests" not in challenge
    assert "hidden_test_data" not in challenge

    # Retrieve challenge via GET /challenge
    get_res = await async_client.get(
        f"/api/v1/assessments/{assessment_id}/challenge",
        headers=USER_A_HEADERS,
    )
    assert get_res.status_code == 200
    retrieved = get_res.json()["challenge"]
    assert "public_tests" in retrieved
    assert "hidden_tests" not in retrieved


@pytest.mark.asyncio
async def test_cross_user_isolation_on_assessments(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Ensure User B cannot access, submit to, or delete User A's assessment."""
    create_res = await async_client.post(
        "/api/v1/assessments",
        headers=USER_A_HEADERS,
        json={"skill_name": "Python", "forced_level": "basic"},
    )
    assert create_res.status_code == 201
    assessment_id = create_res.json()["assessment_id"]

    # User B tries to view challenge -> 404
    res1 = await async_client.get(
        f"/api/v1/assessments/{assessment_id}/challenge",
        headers=USER_B_HEADERS,
    )
    assert res1.status_code == 404

    # User B tries to submit code -> 404
    res2 = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/submit",
        headers=USER_B_HEADERS,
        json={"submitted_code": "def f(): return 1"},
    )
    assert res2.status_code == 404

    # User B tries to view results -> 404
    res3 = await async_client.get(
        f"/api/v1/assessments/{assessment_id}/results",
        headers=USER_B_HEADERS,
    )
    assert res3.status_code == 404

    # User B tries to delete -> 404
    res4 = await async_client.delete(
        f"/api/v1/assessments/{assessment_id}",
        headers=USER_B_HEADERS,
    )
    assert res4.status_code == 404


# -----------------------------------------------------------------------------
# 4. End-to-End Submission & Career Twin Skill Promotion
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_submit_passing_solution_promotes_skill(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Ensure passing solution promotes skill to 'practically_demonstrated' with boosted confidence."""
    # 1. Create Assessment for FastAPI
    create_res = await async_client.post(
        "/api/v1/assessments",
        headers=USER_A_HEADERS,
        json={"skill_name": "FastAPI", "forced_level": "basic"},
    )
    assert create_res.status_code == 201
    assessment_id = create_res.json()["assessment_id"]

    # 2. Retrieve Challenge to inspect entry function
    chal_res = await async_client.get(
        f"/api/v1/assessments/{assessment_id}/challenge",
        headers=USER_A_HEADERS,
    )
    assert chal_res.status_code == 200
    entry_fn = chal_res.json()["challenge"]["entry_function"]

    if entry_fn == "validate_auth_header":
        correct_solution = """
def validate_auth_header(header: str) -> bool:
    \"\"\"Validate auth header.\"\"\"
    if not header or not header.startswith("Bearer "):
        return False
    token = header[7:].strip()
    return len(token) > 0
"""
    else:
        correct_solution = """
def sanitize_query_params(params: dict) -> dict:
    \"\"\"Sanitize query params.\"\"\"
    result = {}
    for k, v in params.items():
        if v is None:
            continue
        v_str = str(v).strip()
        if not v_str:
            continue
        if v_str.isdigit():
            result[k] = int(v_str)
        elif v is True or v is False:
            result[k] = v
        else:
            result[k] = v_str
    return result
"""

    sub_res = await async_client.post(
        f"/api/v1/assessments/{assessment_id}/submit",
        headers=USER_A_HEADERS,
        json={"submitted_code": correct_solution},
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()

    assert sub_data["execution_status"] == "passed"
    assert sub_data["passed"] is True
    assert sub_data["score"] >= 70.0
    assert sub_data["assessment_status"] == "passed"

    # Verify hidden test counts reported without leaking data
    assert "passed_count" in sub_data["hidden_results"]
    assert "total_count" in sub_data["hidden_results"]

    # Verify Rubric Feedback
    rubric = sub_data["rubric_feedback"]
    assert len(rubric["criteria"]) == 4
    assert "verified practical competency" in rubric["summary_verdict"].lower()

    # 3. Verify Career Twin Skill Promotion in Database
    stmt_skill = select(StudentSkill).where(
        StudentSkill.firebase_uid == "usr_student_alpha",
        StudentSkill.skill_name.ilike("FastAPI"),
    )
    skill = (await db_session.execute(stmt_skill)).scalar_one_or_none()
    assert skill is not None
    assert skill.verification_status == "practically_demonstrated"
    assert skill.confidence_score >= 0.90
    assert any(e.get("type") == "practical_demonstration" for e in skill.evidence)
