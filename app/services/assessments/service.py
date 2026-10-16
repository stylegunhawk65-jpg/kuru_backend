"""High-level Practical Assessment Service managing assessment lifecycle, scoring, and Career Twin integration."""

from datetime import datetime, timezone
import logging
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import AssessmentSubmission, PracticalAssessment
from app.models.profile import StudentProfile
from app.models.skill import StudentSkill
from app.models.skillproof import SkillProofRun
from app.services.assessments.evaluator import assessment_evaluator
from app.services.assessments.generator import challenge_generator, level_selector

logger = logging.getLogger("kuru.assessments.service")


class PracticalAssessmentService:
    """Manages assessment creation, submission evaluation, and Career Twin integration."""

    @classmethod
    async def create_assessment(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        skill_name: str,
        repository_id: str | None = None,
        forced_level: str | None = None,
    ) -> PracticalAssessment:
        """Create an adaptive practical assessment grounded in student profile and repository evidence."""
        # 1. Fetch Profile
        stmt_prof = select(StudentProfile).where(StudentProfile.firebase_uid == firebase_uid)
        profile = (await db.execute(stmt_prof)).scalar_one_or_none()

        # 2. Fetch Skill
        stmt_skill = select(StudentSkill).where(
            StudentSkill.firebase_uid == firebase_uid,
            StudentSkill.skill_name.ilike(skill_name),
        )
        student_skill = (await db.execute(stmt_skill)).scalar_one_or_none()

        # 3. Fetch latest SkillProof run if repository specified
        skillproof_run = None
        if repository_id:
            stmt_sp = (
                select(SkillProofRun)
                .where(
                    SkillProofRun.firebase_uid == firebase_uid,
                    SkillProofRun.repository_id == repository_id,
                )
                .order_by(SkillProofRun.created_at.desc())
            )
            skillproof_run = (await db.execute(stmt_sp)).scalars().first()

        # 4. Adaptive Level Selection
        if forced_level and forced_level.lower() in ("basic", "intermediate", "advanced"):
            level = forced_level.lower()
            challenge_type = "coding"
            rationale = f"Level '{level}' specified by user."
        else:
            level, challenge_type, rationale = level_selector.select_level(
                skill_name=skill_name,
                student_skill=student_skill,
                skillproof_run=skillproof_run,
                profile=profile,
            )

        # 5. Generate Challenge with bounded retries & fallback templates
        challenge_data = await challenge_generator.generate_challenge(
            skill_name=skill_name,
            level=level,
            challenge_type=challenge_type,
        )

        public_challenge = {
            "title": challenge_data["title"],
            "description": challenge_data["description"],
            "entry_function": challenge_data["entry_function"],
            "starter_code": challenge_data["starter_code"],
            "public_tests": challenge_data.get("public_tests", []),
            "difficulty": challenge_data["difficulty"],
            "rubric": challenge_data.get("rubric", {}),
        }
        hidden_tests = challenge_data.get("hidden_tests", [])

        # 6. Persist PracticalAssessment
        assessment = PracticalAssessment(
            firebase_uid=firebase_uid,
            repository_id=repository_id,
            repository_full_name=skillproof_run.repository_full_name if skillproof_run else None,
            skill_name=skill_name,
            assessment_level=level,
            challenge_type=challenge_type,
            status="pending",
            challenge_data=public_challenge,
            hidden_test_data=hidden_tests,
            attempt_count=0,
            max_attempts=3,
            level_selection_rationale=rationale,
        )
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)

        logger.info("Created %s practical assessment %s for user %s", level, assessment.id, firebase_uid)
        return assessment

    @classmethod
    async def get_challenge_public(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        assessment_id: str,
    ) -> dict[str, Any]:
        """Retrieve challenge data with hidden tests strictly stripped."""
        stmt = select(PracticalAssessment).where(
            PracticalAssessment.id == assessment_id,
            PracticalAssessment.firebase_uid == firebase_uid,
        )
        assessment = (await db.execute(stmt)).scalar_one_or_none()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found.",
            )

        # Ensure hidden tests are never leaked
        challenge = dict(assessment.challenge_data)
        challenge.pop("hidden_tests", None)

        return {
            "assessment_id": assessment.id,
            "skill_name": assessment.skill_name,
            "assessment_level": assessment.assessment_level,
            "challenge_type": assessment.challenge_type,
            "status": assessment.status,
            "attempt_count": assessment.attempt_count,
            "max_attempts": assessment.max_attempts,
            "challenge": challenge,
            "level_selection_rationale": assessment.level_selection_rationale,
        }

    @classmethod
    async def submit_solution(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        assessment_id: str,
        submitted_code: str,
    ) -> dict[str, Any]:
        """Submit code solution, execute in sandbox, record submission, and update Career Twin skills."""
        stmt = select(PracticalAssessment).where(
            PracticalAssessment.id == assessment_id,
            PracticalAssessment.firebase_uid == firebase_uid,
        )
        assessment = (await db.execute(stmt)).scalar_one_or_none()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found.",
            )

        if assessment.attempt_count >= assessment.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum attempt limit ({assessment.max_attempts}) reached for this assessment.",
            )

        # 1. Run Objective Evaluation in Sandbox
        entry_fn = assessment.challenge_data.get("entry_function", "solution")
        public_tests = assessment.challenge_data.get("public_tests", [])
        hidden_tests = assessment.hidden_test_data or []
        rubric = assessment.challenge_data.get("rubric", {})

        eval_result = await assessment_evaluator.evaluate_submission(
            submitted_code=submitted_code,
            entry_function=entry_fn,
            public_tests_data=public_tests,
            hidden_tests_data=hidden_tests,
            rubric=rubric,
        )

        # 2. Record Submission
        attempt_number = assessment.attempt_count + 1
        submission = AssessmentSubmission(
            assessment_id=assessment.id,
            firebase_uid=firebase_uid,
            attempt_number=attempt_number,
            submitted_code=submitted_code,
            execution_status=eval_result["execution_status"],
            public_results=eval_result["public_results"],
            hidden_results=eval_result["hidden_results"],
            score=eval_result["score"],
            rubric_feedback=eval_result["rubric_feedback"],
            execution_metrics=eval_result["execution_metrics"],
        )
        db.add(submission)

        # 3. Update Assessment Record
        assessment.attempt_count = attempt_number
        assessment.score = max(assessment.score or 0.0, eval_result["score"])
        is_passed = eval_result["passed"] or (assessment.passed is True)
        assessment.passed = is_passed

        if is_passed:
            assessment.status = "passed"
            assessment.completed_at = datetime.now(timezone.utc)
        elif attempt_number >= assessment.max_attempts:
            assessment.status = "failed"
            assessment.completed_at = datetime.now(timezone.utc)
        else:
            assessment.status = "in_progress"

        # 4. Career Twin Integration: Update StudentSkill Verification Status
        if is_passed:
            await cls._promote_skill_to_practically_demonstrated(
                db=db,
                firebase_uid=firebase_uid,
                skill_name=assessment.skill_name,
                assessment_id=assessment.id,
                score=eval_result["score"],
                level=assessment.assessment_level,
            )

        await db.commit()
        await db.refresh(submission)
        await db.refresh(assessment)

        return {
            "submission_id": submission.id,
            "assessment_id": assessment.id,
            "attempt_number": attempt_number,
            "execution_status": submission.execution_status,
            "score": submission.score,
            "passed": is_passed,
            "public_results": submission.public_results,
            "hidden_results": submission.hidden_results,
            "rubric_feedback": submission.rubric_feedback,
            "execution_metrics": submission.execution_metrics,
            "assessment_status": assessment.status,
        }

    @classmethod
    async def _promote_skill_to_practically_demonstrated(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        skill_name: str,
        assessment_id: str,
        score: float,
        level: str,
    ) -> None:
        """Promote skill to 'practically_demonstrated' and boost confidence for Career Twin agents."""
        stmt = select(StudentSkill).where(
            StudentSkill.firebase_uid == firebase_uid,
            StudentSkill.skill_name.ilike(skill_name),
        )
        skill = (await db.execute(stmt)).scalar_one_or_none()

        now = datetime.now(timezone.utc).isoformat()
        practical_evidence = {
            "type": "practical_demonstration",
            "assessment_id": assessment_id,
            "assessment_level": level,
            "score": score,
            "verified_at": now,
            "detail": f"Successfully completed {level.capitalize()} practical coding assessment with score {score}%.",
        }

        if skill:
            skill.verification_status = "practically_demonstrated"
            skill.confidence_score = min(1.0, max(float(skill.confidence_score), 0.90))
            ev_list = list(skill.evidence or [])
            ev_list.append(practical_evidence)
            skill.evidence = ev_list
        else:
            # Create new practically demonstrated skill entry
            new_skill = StudentSkill(
                firebase_uid=firebase_uid,
                skill_name=skill_name,
                category="Framework" if "fastapi" in skill_name.lower() or "django" in skill_name.lower() else "Language",
                confidence_score=0.90,
                verification_status="practically_demonstrated",
                evidence=[practical_evidence],
                source_repositories=[],
            )
            db.add(new_skill)

        logger.info(
            "Promoted skill '%s' to practically_demonstrated for user %s (score=%s)",
            skill_name,
            firebase_uid,
            score,
        )


assessment_service = PracticalAssessmentService()
