"""Comprehensive Unit and Integration Tests for Phase 11: Resume & Application Integration.

Tests cover:
1. ATS Resume Generation:
   - Grounded strictly in verified candidate profile, GitHub repos, and practical assessments.
   - Zero hallucination guarantee (never invent skills, companies, degrees, or metrics).
2. Job-Specific Tailoring & Evidence Citations:
   - Aligning resume summary and skills with real target job requirements.
   - Evidence citations linking claims to AST-verified source code paths.
3. Missing Data Graceful Handling:
   - Non-crashing behavior and zero fabrication when candidate profile has empty/missing fields.
4. Pure-Python ATS PDF Export:
   - Generating valid PDF binary bytes with %PDF- header, standard ATS Helvetica typography, and dividers.
5. Resume Lifecycle & CRUD Endpoints:
   - POST /resumes/generate, POST /resumes, GET /resumes, GET /resumes/{id}, PUT /resumes/{id},
     POST /resumes/{id}/regenerate, GET /resumes/{id}/pdf, DELETE /resumes/{id}.
6. Application Preparation & Human-in-the-Loop Approval Queue:
   - Synthesizing application packet and staging approval request.
   - Absolute auto-submission prevention: status remains 'saved', submitted_at is None until approved.
7. Approval Execution Lifecycle:
   - Approving and executing job_application action stamps status='applied' and submitted_at.
8. Application Tracking CRUD & Filtering:
   - GET /applications, GET /applications?status=applied, GET /applications/{job_id},
     PATCH /applications/{job_id}, DELETE /applications/{job_id}.
9. Security, Authentication, & Multi-Tenant Isolation:
   - 401 Unauthorized gates for unauthenticated requests.
   - Cross-user data isolation: Bob cannot view, modify, or delete Alice's resumes or applications.
"""

from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_workflow import AgentApprovalRequest
from app.models.assessment import PracticalAssessment
from app.models.github import GithubRepository
from app.models.job import JobPosting, SavedJob
from app.models.profile import StudentProfile
from app.models.resume import Resume
from app.models.skill import StudentSkill
from app.schemas.resume import ResumeGenerateRequest
from app.services.agents.approval_agent import approval_workflow_agent
from app.services.application_service import application_service
from app.services.llm.mock_provider import MockLLMProvider
from app.services.resume.pdf_exporter import pdf_exporter
from app.services.resume.service import resume_service


# -----------------------------------------------------------------------------
# Auth Mocking & User Test Constants
# -----------------------------------------------------------------------------

USER_ALICE_UID = "usr_phase11_alice"
USER_BOB_UID = "usr_phase11_bob"

USER_ALICE_HEADERS = {"Authorization": "Bearer token_phase11_alice"}
USER_BOB_HEADERS = {"Authorization": "Bearer token_phase11_bob"}


def mock_verify_id_token(token: str, *args, **kwargs):
    if token == "token_phase11_alice":
        return {
            "uid": USER_ALICE_UID,
            "email": "alice@kuru.ai",
            "name": "Alice Candidate",
        }
    elif token == "token_phase11_bob":
        return {
            "uid": USER_BOB_UID,
            "email": "bob@kuru.ai",
            "name": "Bob Candidate",
        }
    raise ValueError("Invalid test token")


@pytest.fixture(autouse=True)
def patch_firebase_auth():
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=mock_verify_id_token):
        yield


@pytest.fixture
def mock_llm_provider() -> MockLLMProvider:
    return MockLLMProvider()


# -----------------------------------------------------------------------------
# Seed Database Fixture
# -----------------------------------------------------------------------------

@pytest.fixture
async def seed_phase11_data(db_session: AsyncSession):
    """Seed Alice with real profile, skills, AST evidence, assessments, and jobs."""
    now = datetime.now(timezone.utc)

    # 1. Profile for Alice
    profile_alice = StudentProfile(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        email="alice@kuru.ai",
        full_name="Alice Candidate",
        bio="Full-Stack Backend Engineer",
        education=[{
            "institution": "IIT Delhi",
            "degree": "Bachelor of Technology",
            "graduation_year": "2025",
            "field_of_study": "Computer Science",
        }],
        target_roles=["Backend Engineer", "API Specialist"],
        interests=["Distributed Systems", "Database Optimization"],
        preferred_locations=["Bengaluru", "Remote"],
    )
    db_session.add(profile_alice)

    # 2. Student Skills for Alice
    skill_python = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        skill_name="Python",
        category="Language",
        confidence_score=0.95,
        verification_status="practically_demonstrated",
        evidence=[{"source": "app/main.py", "lines": [10, 50]}],
        source_repositories=["kuru-backend"],
    )
    skill_fastapi = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        skill_name="FastAPI",
        category="Framework",
        confidence_score=0.90,
        verification_status="practically_demonstrated",
        evidence=[{"source": "app/api/v1/router.py", "lines": [1, 30]}],
        source_repositories=["kuru-backend"],
    )
    skill_postgres = StudentSkill(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        skill_name="PostgreSQL",
        category="Database",
        confidence_score=0.85,
        verification_status="repository_supported",
        evidence=[{"source": "app/db/session.py", "lines": [15, 40]}],
        source_repositories=["kuru-backend"],
    )
    db_session.add_all([skill_python, skill_fastapi, skill_postgres])

    # 3. Practical Assessments for Alice
    assessment_py = PracticalAssessment(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        skill_name="Python",
        assessment_level="intermediate",
        challenge_type="coding",
        status="passed",
        score=92.0,
        passed=True,
        challenge_data={"title": "High-throughput Stream Processing"},
    )
    assessment_fastapi = PracticalAssessment(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        skill_name="FastAPI",
        assessment_level="intermediate",
        challenge_type="coding",
        status="passed",
        score=88.0,
        passed=True,
        challenge_data={"title": "Async Dependency Injection Framework"},
    )
    db_session.add_all([assessment_py, assessment_fastapi])

    # 4. Job Postings
    job_acme = JobPosting(
        id="job_acme_backend",
        source="curated_linkedin",
        source_id="acme_1",
        dedup_hash="hash_acme_1",
        title="Junior Backend Engineer",
        company="Acme Corp",
        location="Bengaluru, India",
        is_remote=False,
        job_type="full_time",
        url="https://acme.example.com/jobs/1",
        description="Looking for Junior Backend Engineer proficient in Python, FastAPI, and Docker.",
        required_skills=["Python", "FastAPI", "Docker"],
        posted_at=now,
        is_active=True,
    )
    job_beta = JobPosting(
        id="job_beta_cloud",
        source="curated_naukri",
        source_id="beta_2",
        dedup_hash="hash_beta_2",
        title="Cloud Operations Engineer",
        company="Beta Cloud",
        location="Remote",
        is_remote=True,
        job_type="full_time",
        url="https://betacloud.example.com/jobs/2",
        description="Seeking Cloud Operations Engineer with AWS, Terraform, and Kubernetes experience.",
        required_skills=["AWS", "Terraform", "Kubernetes"],
        posted_at=now,
        is_active=True,
    )
    db_session.add_all([job_acme, job_beta])

    await db_session.commit()
    return {
        "profile": profile_alice,
        "job_acme": job_acme,
        "job_beta": job_beta,
    }


# -----------------------------------------------------------------------------
# 1. Anti-Hallucination Resume Generation Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_generation_zero_hallucination(
    db_session: AsyncSession, seed_phase11_data
):
    """Verify resume strictly reflects candidate profile, skills, AST files, and assessments."""
    resume_obj = await resume_service.generate_resume(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        request=ResumeGenerateRequest(save_to_db=True),
    )

    assert resume_obj.id is not None
    assert resume_obj.firebase_uid == USER_ALICE_UID
    assert resume_obj.contact_info["full_name"] == "Alice Candidate"
    assert resume_obj.contact_info["email"] == "alice@kuru.ai"

    # Education matches seeded record strictly
    assert len(resume_obj.education) == 1
    edu = resume_obj.education[0]
    assert edu["institution"] == "IIT Delhi"
    assert edu["degree"] == "Bachelor of Technology"
    assert edu["graduation_year"] == "2025"

    # Skills contain only verified skills
    skills_map = resume_obj.skills_by_category
    assert "Languages" in skills_map
    lang_skill_names = [s["skill_name"] for s in skills_map["Languages"]]
    assert "Python" in lang_skill_names

    assert "Frameworks & Libraries" in skills_map
    fw_skill_names = [s["skill_name"] for s in skills_map["Frameworks & Libraries"]]
    assert "FastAPI" in fw_skill_names

    # Zero hallucination check: unverified skills are NOT present
    for cat, skills in skills_map.items():
        for s in skills:
            assert s["skill_name"] not in ["React", "Rust", "Kubernetes", "C++"]

    # Practical assessments reflect real completed assessments
    assert len(resume_obj.practical_assessments) == 2
    ass_map = {a["skill_name"]: a for a in resume_obj.practical_assessments}
    assert "Python" in ass_map
    assert ass_map["Python"]["score"] == 92.0
    assert ass_map["Python"]["passed"] is True

    # Tailoring metadata and citations
    meta = resume_obj.tailoring_metadata
    assert "Anti-Hallucination Guarantee" in meta["honest_disclaimer"]
    assert "Python" in meta["evidence_citations"]
    assert any("app/main.py" in cite for cite in meta["evidence_citations"]["Python"])


# -----------------------------------------------------------------------------
# 2. Job-Specific Tailoring & Citations Map
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_specific_tailoring_and_citations(
    db_session: AsyncSession, seed_phase11_data
):
    """Verify resume tailored for a real job aligns skills, highlights match, and notes gaps."""
    resume_obj = await resume_service.generate_resume(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        request=ResumeGenerateRequest(
            target_role="Junior Backend Engineer",
            job_id="job_acme_backend",
            save_to_db=True,
        ),
    )

    assert resume_obj.target_role == "Junior Backend Engineer"
    assert resume_obj.job_id == "job_acme_backend"

    meta = resume_obj.tailoring_metadata
    assert meta["company"] == "Acme Corp"
    assert "Python" in meta["matching_skills"]
    assert "FastAPI" in meta["matching_skills"]
    assert "Docker" in meta["missing_skills"]

    # Summary is grounded in verified skills
    summary = resume_obj.summary
    assert "Junior Backend Engineer" in summary or "Backend" in summary
    assert "Python" in summary


# -----------------------------------------------------------------------------
# 3. Missing Profile Data Handled Gracefully
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_profile_data_graceful_handling(
    db_session: AsyncSession
):
    """Verify a user with minimal/no profile data generates safely without fake placeholders."""
    minimal_uid = "usr_minimal_profile"

    # Minimal profile with only email
    prof = StudentProfile(
        id=str(uuid.uuid4()),
        firebase_uid=minimal_uid,
        email="minimal@kuru.ai",
        full_name="Candidate",
        education=[],
        target_roles=[],
        interests=[],
        preferred_locations=[],
    )
    db_session.add(prof)
    await db_session.commit()

    resume_obj = await resume_service.generate_resume(
        db=db_session,
        firebase_uid=minimal_uid,
        request=ResumeGenerateRequest(save_to_db=True),
    )

    assert resume_obj.contact_info["email"] == "minimal@kuru.ai"
    assert resume_obj.contact_info["full_name"] == "Candidate"
    assert resume_obj.education == []
    assert resume_obj.practical_assessments == []
    assert resume_obj.projects == []
    assert "Anti-Hallucination Guarantee" in resume_obj.tailoring_metadata["honest_disclaimer"]


# -----------------------------------------------------------------------------
# 4. Pure-Python ATS PDF Generation & Export
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pdf_export_structure_and_bytes(
    db_session: AsyncSession, seed_phase11_data
):
    """Verify ReportLab produces valid ATS PDF binary with proper %PDF- header and layout."""
    resume_obj = await resume_service.generate_resume(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        request=ResumeGenerateRequest(
            target_role="Junior Backend Engineer",
            job_id="job_acme_backend",
            save_to_db=True,
        ),
    )

    pdf_bytes = pdf_exporter.export_resume_pdf(resume_obj)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF specification magic byte header
    assert pdf_bytes.startswith(b"%PDF-")
    # Verify standard ATS Helvetica font inclusion
    assert b"Helvetica" in pdf_bytes


# -----------------------------------------------------------------------------
# 5. Resume CRUD & PDF Endpoint Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_crud_and_endpoints(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Verify /api/v1/resumes API endpoints for generation, CRUD, PDF download, and regeneration."""
    # 1. Generate via API
    gen_res = await async_client.post(
        "/api/v1/resumes/generate",
        json={"target_role": "Junior Backend Engineer", "job_id": "job_acme_backend", "save_to_db": True},
        headers=USER_ALICE_HEADERS,
    )
    assert gen_res.status_code == 201
    created_resume = gen_res.json()
    resume_id = created_resume["id"]
    assert created_resume["contact_info"]["full_name"] == "Alice Candidate"

    # 2. List Resumes
    list_res = await async_client.get("/api/v1/resumes", headers=USER_ALICE_HEADERS)
    assert list_res.status_code == 200
    resumes_list = list_res.json()
    assert len(resumes_list) >= 1
    assert any(r["id"] == resume_id for r in resumes_list)

    # 3. Get Resume Details
    get_res = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=USER_ALICE_HEADERS)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == resume_id

    # 4. Update Resume
    update_res = await async_client.put(
        f"/api/v1/resumes/{resume_id}",
        json={"summary": "Updated tailored summary for Acme Corp.", "is_primary": True},
        headers=USER_ALICE_HEADERS,
    )
    assert update_res.status_code == 200
    assert update_res.json()["summary"] == "Updated tailored summary for Acme Corp."
    assert update_res.json()["is_primary"] is True

    # 5. Download ATS PDF Binary
    pdf_res = await async_client.get(f"/api/v1/resumes/{resume_id}/pdf", headers=USER_ALICE_HEADERS)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_res.headers["content-disposition"]
    assert pdf_res.content.startswith(b"%PDF-")

    # 6. Regenerate Resume
    regen_res = await async_client.post(
        f"/api/v1/resumes/{resume_id}/regenerate",
        headers=USER_ALICE_HEADERS,
    )
    assert regen_res.status_code == 200
    assert regen_res.json()["id"] == resume_id

    # 7. Delete Resume
    del_res = await async_client.delete(f"/api/v1/resumes/{resume_id}", headers=USER_ALICE_HEADERS)
    assert del_res.status_code == 204

    # Confirm 404 after deletion
    get_deleted = await async_client.get(f"/api/v1/resumes/{resume_id}", headers=USER_ALICE_HEADERS)
    assert get_deleted.status_code == 404


# -----------------------------------------------------------------------------
# 6. Application Preparation & Human-in-the-Loop Approval Queue
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_application_preparation_and_approval_gate(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Verify application packet preparation stages an AgentApprovalRequest and NEVER auto-submits."""
    payload = {
        "job_id": "job_acme_backend",
        "notes": "Targeting backend position; referred by college alumni.",
        "deadline": "2026-11-30",
    }

    prep_res = await async_client.post(
        "/api/v1/applications/prepare",
        json=payload,
        headers=USER_ALICE_HEADERS,
    )
    assert prep_res.status_code == 201
    prep_data = prep_res.json()

    assert prep_data["job_id"] == "job_acme_backend"
    assert prep_data["status"] == "pending_approval"
    approval_id = prep_data["approval_request_id"]
    assert approval_id is not None and len(approval_id) > 0

    packet = prep_data["application_packet"]
    assert packet["requires_human_approval"] is True
    assert packet["auto_submission_prevented"] is True
    assert "Python" in packet["matching_skills"]
    assert "Docker" in packet["missing_skills"]
    assert "Dear Acme Corp Hiring Team" in packet["cover_note"]

    # Verify SavedJob state in database: must be saved, NOT applied!
    sj_stmt = select(SavedJob).where(
        SavedJob.firebase_uid == USER_ALICE_UID,
        SavedJob.job_id == "job_acme_backend",
    )
    saved_job = (await db_session.execute(sj_stmt)).scalar_one()
    assert saved_job.status == "saved"
    assert saved_job.submitted_at is None
    assert saved_job.deadline is not None
    assert saved_job.deadline.strftime("%Y-%m-%d") == "2026-11-30"
    assert saved_job.resume_id is not None

    # Verify AgentApprovalRequest queued in database
    approval_stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.id == approval_id)
    approval_req = (await db_session.execute(approval_stmt)).scalar_one()
    assert approval_req.status == "pending"
    assert approval_req.action_type == "job_application"
    assert approval_req.target_entity_id == "job_acme_backend"


# -----------------------------------------------------------------------------
# 7. Approval Execution Lifecycle: Transition to Applied
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approval_execution_marks_applied(
    db_session: AsyncSession, seed_phase11_data
):
    """Verify explicit human approval execution transitions application status to applied and stamps submitted_at."""
    # 1. Prepare application
    prep_res = await application_service.prepare_application(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        request=type("MockReq", (), {
            "job_id": "job_acme_backend",
            "resume_id": None,
            "cover_note": None,
            "notes": "Testing approval execution",
            "deadline": None,
        })(),
    )

    approval_id = prep_res.approval_request_id

    # 2. Decide approval -> approve
    decided_req = await approval_workflow_agent.decide_approval(
        db=db_session,
        approval_id=approval_id,
        firebase_uid=USER_ALICE_UID,
        decision="approved",
        decision_notes="Looks great, submitting application.",
    )
    assert decided_req.status == "approved"

    # 3. Execute approved action
    exec_res = await approval_workflow_agent.execute_approved_action(
        db=db_session,
        approval=decided_req,
    )
    assert exec_res["status"] == "success"
    assert exec_res["action_type"] == "job_application"

    # 4. Verify SavedJob tracking status is now applied
    sj_stmt = select(SavedJob).where(
        SavedJob.firebase_uid == USER_ALICE_UID,
        SavedJob.job_id == "job_acme_backend",
    )
    saved_job = (await db_session.execute(sj_stmt)).scalar_one()
    assert saved_job.status == "applied"
    assert saved_job.submitted_at is not None
    assert isinstance(saved_job.submitted_at, datetime)


# -----------------------------------------------------------------------------
# 8. Application Tracking CRUD & Status Filtering
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_application_tracking_crud_and_filtering(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Verify /api/v1/applications listing, detail lookup, status updates, and deletion."""
    # Prepare two applications
    await application_service.prepare_application(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        request=type("MockReq", (), {
            "job_id": "job_acme_backend",
            "resume_id": None,
            "cover_note": None,
            "notes": "Acme application",
            "deadline": "2026-12-01",
        })(),
    )

    await application_service.prepare_application(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        request=type("MockReq", (), {
            "job_id": "job_beta_cloud",
            "resume_id": None,
            "cover_note": None,
            "notes": "Beta Cloud application",
            "deadline": "2026-12-15",
        })(),
    )

    # 1. List all applications
    list_res = await async_client.get("/api/v1/applications", headers=USER_ALICE_HEADERS)
    assert list_res.status_code == 200
    apps = list_res.json()
    assert len(apps) == 2

    # 2. Update status of Acme to 'interviewing'
    patch_res = await async_client.patch(
        "/api/v1/applications/job_acme_backend",
        json={"status": "interviewing", "notes": "Technical round scheduled for next Tuesday."},
        headers=USER_ALICE_HEADERS,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "interviewing"
    assert patch_res.json()["notes"] == "Technical round scheduled for next Tuesday."

    # 3. Filter by status
    filter_res = await async_client.get(
        "/api/v1/applications?status=interviewing",
        headers=USER_ALICE_HEADERS,
    )
    assert filter_res.status_code == 200
    filtered_apps = filter_res.json()
    assert len(filtered_apps) == 1
    assert filtered_apps[0]["job_id"] == "job_acme_backend"

    # 4. Get single application detail
    detail_res = await async_client.get(
        "/api/v1/applications/job_acme_backend",
        headers=USER_ALICE_HEADERS,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["job"]["company"] == "Acme Corp"

    # 5. Delete an application
    del_res = await async_client.delete(
        "/api/v1/applications/job_beta_cloud",
        headers=USER_ALICE_HEADERS,
    )
    assert del_res.status_code == 204

    # Confirm list now has 1
    list_after = await async_client.get("/api/v1/applications", headers=USER_ALICE_HEADERS)
    assert len(list_after.json()) == 1


# -----------------------------------------------------------------------------
# 9. Security, Authentication, & Multi-Tenant Cross-User Isolation
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resume_application_cross_user_isolation(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Verify User Bob cannot access, update, or delete User Alice's resumes and applications."""
    # Alice generates a resume
    gen_res = await async_client.post(
        "/api/v1/resumes/generate",
        json={"target_role": "Backend Engineer", "job_id": "job_acme_backend", "save_to_db": True},
        headers=USER_ALICE_HEADERS,
    )
    assert gen_res.status_code == 201
    alice_resume_id = gen_res.json()["id"]

    # Alice prepares an application
    prep_res = await async_client.post(
        "/api/v1/applications/prepare",
        json={"job_id": "job_acme_backend"},
        headers=USER_ALICE_HEADERS,
    )
    assert prep_res.status_code == 201

    # 1. Bob attempts to access Alice's resume -> 404
    bob_get_resume = await async_client.get(
        f"/api/v1/resumes/{alice_resume_id}",
        headers=USER_BOB_HEADERS,
    )
    assert bob_get_resume.status_code == 404

    # 2. Bob attempts to download Alice's PDF -> 404
    bob_pdf = await async_client.get(
        f"/api/v1/resumes/{alice_resume_id}/pdf",
        headers=USER_BOB_HEADERS,
    )
    assert bob_pdf.status_code == 404

    # 3. Bob attempts to update Alice's resume -> 404
    bob_put_resume = await async_client.put(
        f"/api/v1/resumes/{alice_resume_id}",
        json={"summary": "Hacked summary"},
        headers=USER_BOB_HEADERS,
    )
    assert bob_put_resume.status_code == 404

    # 4. Bob attempts to delete Alice's resume -> 404
    bob_del_resume = await async_client.delete(
        f"/api/v1/resumes/{alice_resume_id}",
        headers=USER_BOB_HEADERS,
    )
    assert bob_del_resume.status_code == 404

    # 5. Bob attempts to get Alice's application -> 404
    bob_get_app = await async_client.get(
        "/api/v1/applications/job_acme_backend",
        headers=USER_BOB_HEADERS,
    )
    assert bob_get_app.status_code == 404

    # 6. Bob attempts to patch Alice's application -> 404
    bob_patch_app = await async_client.patch(
        "/api/v1/applications/job_acme_backend",
        json={"status": "rejected"},
        headers=USER_BOB_HEADERS,
    )
    assert bob_patch_app.status_code == 404

    # 7. Bob lists applications -> empty list (Alice's applications isolated)
    bob_list_apps = await async_client.get(
        "/api/v1/applications",
        headers=USER_BOB_HEADERS,
    )
    assert bob_list_apps.status_code == 200
    assert bob_list_apps.json() == []

    # 8. Unauthenticated requests are rejected with 401
    unauth_resume = await async_client.get("/api/v1/resumes")
    assert unauth_resume.status_code == 401

    unauth_app = await async_client.get("/api/v1/applications")
    assert unauth_app.status_code == 401


@pytest.mark.asyncio
async def test_resume_generation_github_repository_language_regression(
    db_session: AsyncSession, seed_phase11_data
):
    """Regression test ensuring resume generation succeeds without 'language' attribute crashes.
    
    Verifies that GithubRepository instances with missing or differently stored language metadata
    (primary_language=None, primary_language='Rust', or legacy .language accessor) do not crash
    and generate valid ATS project items.
    """
    repo_null_lang = GithubRepository(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        github_repo_id="repo_regression_null",
        name="kuru_null_lang",
        full_name="alice/kuru_null_lang",
        html_url="https://github.com/alice/kuru_null_lang",
        primary_language=None,
        stars_count=12,
        forks_count=3,
        selected_for_analysis=True,
    )
    repo_rust_lang = GithubRepository(
        id=str(uuid.uuid4()),
        firebase_uid=USER_ALICE_UID,
        github_repo_id="repo_regression_rust",
        name="kuru_rust_core",
        full_name="alice/kuru_rust_core",
        html_url="https://github.com/alice/kuru_rust_core",
        primary_language="Rust",
        stars_count=45,
        forks_count=5,
        selected_for_analysis=True,
    )
    db_session.add_all([repo_null_lang, repo_rust_lang])
    await db_session.commit()

    # Test model attribute compatibility
    assert repo_null_lang.language is None
    assert repo_null_lang.stargazers_count == 12
    assert repo_rust_lang.language == "Rust"
    assert repo_rust_lang.stargazers_count == 45

    # Generate resume through resume_service
    request = ResumeGenerateRequest(
        target_role="Systems Engineer",
        job_id="job_acme_backend",
        save_to_db=False,
    )
    resume_response = await resume_service.generate_resume(
        db=db_session,
        firebase_uid=USER_ALICE_UID,
        request=request,
    )

    assert resume_response is not None
    assert resume_response.target_role == "Systems Engineer"
    
    # Verify projects were generated from repositories without crash
    project_titles = [
        p["title"].lower() if isinstance(p, dict) else p.title.lower()
        for p in resume_response.projects
    ]
    assert any("kuru rust core" in t for t in project_titles)
    assert any("kuru null lang" in t for t in project_titles)


@pytest.mark.asyncio
async def test_multi_repository_selection_and_dynamic_career_readiness(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Test multi-repository selection and dynamic Career Readiness recalculation."""
    # 1. Initially check Career Twin readiness
    ct_res = await async_client.get("/api/v1/career-twin", headers=USER_ALICE_HEADERS)
    assert ct_res.status_code == 200
    ct_data = ct_res.json()
    assert "readiness_score" in ct_data
    assert "is_insufficient_data" in ct_data

    # 2. Deselect all repositories (select empty list)
    select_empty_res = await async_client.post(
        "/api/v1/github/repos/select",
        json={"repo_ids": []},
        headers=USER_ALICE_HEADERS,
    )
    assert select_empty_res.status_code == 200
    assert len([r for r in select_empty_res.json() if r.get("selected_for_analysis")]) == 0

    # 3. Career Twin should now honestly report insufficient data
    ct_empty_res = await async_client.get("/api/v1/career-twin", headers=USER_ALICE_HEADERS)
    assert ct_empty_res.status_code == 200
    empty_data = ct_empty_res.json()
    assert empty_data["readiness_score"] == 0
    assert empty_data["is_insufficient_data"] is True
    assert empty_data["selected_repositories_count"] == 0
    assert "select at least one" in empty_data["score_explanation"].lower()
    assert len(empty_data["next_recommended_actions"]) > 0

    # 4. Select specific repository
    repo_alice = GithubRepository(
        id="repo_alice_selected",
        firebase_uid=USER_ALICE_UID,
        github_repo_id="gh_repo_alice_1",
        name="alice_portfolio",
        full_name="alice/alice_portfolio",
        html_url="https://github.com/alice/alice_portfolio",
        primary_language="Python",
        stars_count=10,
        forks_count=2,
        selected_for_analysis=False,
    )
    db_session.add(repo_alice)
    await db_session.commit()

    select_res = await async_client.post(
        "/api/v1/github/repos/select",
        json={"repo_ids": ["repo_alice_selected"]},
        headers=USER_ALICE_HEADERS,
    )
    assert select_res.status_code == 200
    assert len([r for r in select_res.json() if r.get("selected_for_analysis")]) == 1

    # 5. Career Twin should now reflect selected repo
    ct_selected_res = await async_client.get("/api/v1/career-twin", headers=USER_ALICE_HEADERS)
    assert ct_selected_res.status_code == 200
    selected_data = ct_selected_res.json()
    assert selected_data["selected_repositories_count"] == 1
    assert selected_data["is_insufficient_data"] is False
    assert selected_data["readiness_score"] > 0


@pytest.mark.asyncio
async def test_repository_detail_and_skillproof_similarity(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Test detailed repository analysis and SkillProof similarity findings endpoint."""
    repo_alice = GithubRepository(
        id="repo_detail_test",
        firebase_uid=USER_ALICE_UID,
        github_repo_id="gh_detail_1",
        name="kuru_engine",
        full_name="alice/kuru_engine",
        html_url="https://github.com/alice/kuru_engine",
        description="Core AST evaluation engine for Kuru",
        primary_language="Python",
        stars_count=25,
        forks_count=5,
        selected_for_analysis=True,
    )
    db_session.add(repo_alice)
    await db_session.commit()

    res = await async_client.get("/api/v1/github/repos/repo_detail_test/detail", headers=USER_ALICE_HEADERS)
    assert res.status_code == 200
    detail = res.json()
    assert detail["name"] == "kuru_engine"
    assert detail["primary_language"] == "Python"
    assert "honest_reporting" in detail
    assert detail["honest_reporting"]["plagiarism_claim"] is False
    assert detail["honest_reporting"]["ai_generation_claim"] is False
    assert "investigation_bands" in detail["honest_reporting"]
    assert "below_25" in detail["honest_reporting"]["investigation_bands"]
    assert "practical_assessment" in detail


@pytest.mark.asyncio
async def test_base_cv_upload_confirmation_and_tailoring(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Test Master Base CV upload, parsing, confirmation, and integration into tailored resume."""
    # 1. Prepare minimal valid PDF
    pdf_content = b"%PDF-1.4\nCandidate: Alice Walker\nEmail: alice.walker@example.com\nPhone: +1 555-0199\nEDUCATION: B.S. Computer Science, MIT, 2024\nEXPERIENCE: Senior Python Engineer at Tech Innovators (2022 - 2024)\nSKILLS: Python, FastAPI, Docker, PostgreSQL\n%%EOF"
    
    files = {"file": ("Alice_Master_CV.pdf", pdf_content, "application/pdf")}
    upload_res = await async_client.post(
        "/api/v1/resumes/cv/upload",
        files=files,
        headers=USER_ALICE_HEADERS,
    )
    assert upload_res.status_code == 201
    uploaded_cv = upload_res.json()
    assert uploaded_cv["filename"] == "Alice_Master_CV.pdf"
    assert "alice.walker@example.com" in uploaded_cv["email"]

    # 2. Retrieve Base CV
    get_res = await async_client.get("/api/v1/resumes/cv", headers=USER_ALICE_HEADERS)
    assert get_res.status_code == 200
    assert get_res.json()["filename"] == "Alice_Master_CV.pdf"

    # 3. Confirm Base CV
    confirm_res = await async_client.put(
        "/api/v1/resumes/cv/confirm",
        json={
            "full_name": "Alice Walker, M.S.",
            "email": "alice.walker@example.com",
            "phone": "+1 555-0199",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"],
            "experience": [{"title": "Senior Python Engineer", "company": "Tech Innovators", "duration": "2022 - 2024"}],
            "education": [{"degree": "B.S. Computer Science", "institution": "MIT", "year": "2024"}],
        },
        headers=USER_ALICE_HEADERS,
    )
    assert confirm_res.status_code == 200
    confirmed = confirm_res.json()
    assert confirmed["is_confirmed"] is True
    assert confirmed["full_name"] == "Alice Walker, M.S."

    # 4. Tailor a resume: should now seamlessly blend confirmed Master CV baseline
    tailor_res = await async_client.post(
        "/api/v1/resumes/tailor",
        json={
            "target_role": "Lead Backend Architect",
            "target_company": "Apex Cloud Systems",
        },
        headers=USER_ALICE_HEADERS,
    )
    assert tailor_res.status_code == 200
    tailored = tailor_res.json()
    assert tailored["target_role"] == "Lead Backend Architect"
    assert tailored["tailoring_metadata"]["company"] == "Apex Cloud Systems"
    # Candidate name in contact_info should match Alice Walker, M.S.
    assert "Alice Walker" in tailored["contact_info"]["full_name"]


@pytest.mark.asyncio
async def test_individual_skill_selection_and_targeted_analysis_modes(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Test per-repository individual skill selection persistence and explicit analysis modes."""
    # 1. Create a repository
    repo_alice = GithubRepository(
        id="repo_skill_select_test",
        firebase_uid=USER_ALICE_UID,
        github_repo_id="gh_select_1",
        name="kuru_pipeline",
        full_name="alice/kuru_pipeline",
        html_url="https://github.com/alice/kuru_pipeline",
        primary_language="Python",
        stars_count=18,
        selected_for_analysis=True,
    )
    db_session.add(repo_alice)
    await db_session.commit()

    # 2. Persist individual skill selection
    sel_res = await async_client.post(
        "/api/v1/github/repos/repo_skill_select_test/skills/select",
        json={"selected_skills": ["Python", "FastAPI"]},
        headers=USER_ALICE_HEADERS,
    )
    assert sel_res.status_code == 200
    sel_data = sel_res.json()
    assert sel_data["repository_id"] == "repo_skill_select_test"
    assert "Python" in sel_data["selected_skills"]
    assert "FastAPI" in sel_data["selected_skills"]

    # 3. Retrieve persisted skill selections
    get_sel_res = await async_client.get(
        "/api/v1/github/repos/repo_skill_select_test/skills/selected",
        headers=USER_ALICE_HEADERS,
    )
    assert get_sel_res.status_code == 200
    assert get_sel_res.json()["selected_skills"] == ["Python", "FastAPI"]

    # 4. Detail endpoint reflects selected_skills
    detail_res = await async_client.get(
        "/api/v1/github/repos/repo_skill_select_test/detail",
        headers=USER_ALICE_HEADERS,
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert "selected_skills" in detail_data
    assert detail_data["selected_skills"] == ["Python", "FastAPI"]

    # 5. Execute targeted analysis mode (Selected Skills)
    with patch("app.services.github_client.GitHubClient.get_repository_languages", return_value={"Python": 12000}), \
         patch("app.services.github_client.GitHubClient.get_repository_tree", return_value=[{"path": "main.py", "type": "blob"}]), \
         patch("app.services.github_client.GitHubClient.get_file_content", return_value="import fastapi\napp = fastapi.FastAPI()\n"):
        analyze_res = await async_client.post(
            "/api/v1/github/analyze",
            json={
                "repo_ids": ["repo_skill_select_test"],
                "mode": "selected_skills",
                "selected_skills": ["Python"],
            },
            headers=USER_ALICE_HEADERS,
        )
        assert analyze_res.status_code == 200
        an_data = analyze_res.json()
        assert "selected skills" in an_data["message"]
        analysis_item = an_data["analyses"][0]
        assert analysis_item["file_tree_summary"]["analysis_mode"] == "selected_skills"


@pytest.mark.asyncio
async def test_growth_projects_mapped_to_skill_gaps(
    async_client: AsyncClient, db_session: AsyncSession, seed_phase11_data
):
    """Test that portfolio project recommendations directly target verified candidate skill gaps."""
    res = await async_client.get("/api/v1/growth/projects", headers=USER_ALICE_HEADERS)
    assert res.status_code == 200
    projects = res.json()
    assert len(projects) >= 2

    for p in projects:
        assert "target_skill_gap" in p
        assert "gap_explanation" in p
        assert "milestones" in p
        assert "validation_criteria" in p
        assert "deliverable" in p
        assert "verified_resources" in p
        # Every verified resource has genuine domain
        for r in p["verified_resources"]:
            assert "url" in r
            assert r["url"].startswith("http")



