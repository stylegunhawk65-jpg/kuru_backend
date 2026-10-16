"""Objective evaluation and rubric-based assessment engine.

Separates objective correctness from LLM rubric explanations.
Never lets LLM alone determine pass/fail.
"""

import ast
import logging
from typing import Any

from app.services.assessments.sandbox import (
    ExecutionResult,
    TestCase,
    TestResult,
    sandbox_runner,
)

logger = logging.getLogger("kuru.assessments.evaluator")

PASSING_SCORE_THRESHOLD = 70.0


class AssessmentEvaluator:
    """Evaluates student code submissions through objective testing and rubric scoring."""

    @staticmethod
    def _parse_test_cases(
        public_tests_data: list[dict[str, Any]],
        hidden_tests_data: list[dict[str, Any]],
        entry_function: str,
    ) -> list[TestCase]:
        """Convert test data dictionaries into TestCase objects."""
        cases: list[TestCase] = []

        for t in public_tests_data:
            cases.append(
                TestCase(
                    name=t.get("name", "public_test"),
                    function_name=t.get("function_name", entry_function),
                    args=t.get("args", []),
                    kwargs=t.get("kwargs", {}),
                    expected=t.get("expected"),
                    is_hidden=False,
                )
            )

        for t in hidden_tests_data:
            cases.append(
                TestCase(
                    name=t.get("name", "hidden_test"),
                    function_name=t.get("function_name", entry_function),
                    args=t.get("args", []),
                    kwargs=t.get("kwargs", {}),
                    expected=t.get("expected"),
                    is_hidden=True,
                )
            )

        return cases

    @classmethod
    async def evaluate_submission(
        cls,
        submitted_code: str,
        entry_function: str,
        public_tests_data: list[dict[str, Any]],
        hidden_tests_data: list[dict[str, Any]],
        rubric: dict[str, int] | None = None,
        language: str = "Python",
    ) -> dict[str, Any]:
        """Run isolated sandbox evaluation and calculate rubric breakdown.
        
        Pass/fail is strictly anchored in objective test results.
        """
        all_test_cases = cls._parse_test_cases(public_tests_data, hidden_tests_data, entry_function)

        # 1. Execute in isolated sandbox
        exec_result: ExecutionResult = await sandbox_runner.execute(
            submitted_code=submitted_code,
            test_cases=all_test_cases,
            language=language,
        )

        # 2. Extract public and hidden test tallies
        public_results: list[dict[str, Any]] = []
        hidden_results: list[dict[str, Any]] = []

        public_passed = 0
        public_total = 0
        hidden_passed = 0
        hidden_total = 0

        for r in exec_result.test_results:
            if not r.is_hidden:
                public_total += 1
                if r.passed:
                    public_passed += 1
                public_results.append({
                    "name": r.name,
                    "passed": r.passed,
                    "actual": r.actual,
                    "expected": r.expected,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                })
            else:
                hidden_total += 1
                if r.passed:
                    hidden_passed += 1
                # NEVER leak hidden expected or actual values to prevent reverse engineering
                hidden_results.append({
                    "name": r.name,
                    "passed": r.passed,
                    "error": "Failed hidden assertion" if not r.passed else None,
                    "duration_ms": r.duration_ms,
                })

        # 3. Calculate Objective Score
        total_tests = public_total + hidden_total
        total_passed = public_passed + hidden_passed

        if total_tests > 0:
            score = round((total_passed / total_tests) * 100.0, 1)
        else:
            score = 0.0

        if exec_result.status == "security_violation":
            score = 0.0
            passed = False
        elif exec_result.status == "timeout":
            score = 0.0
            passed = False
        elif exec_result.status in ("runtime_error", "execution_disabled"):
            passed = False
        else:
            # Objective pass threshold: must pass >= 70% and all public tests
            passed = score >= PASSING_SCORE_THRESHOLD and public_passed == public_total

        # 4. Compute Rubric Feedback Breakdown
        rubric_feedback = cls._calculate_rubric(
            score=score,
            public_passed=public_passed,
            public_total=public_total,
            hidden_passed=hidden_passed,
            hidden_total=hidden_total,
            exec_result=exec_result,
            submitted_code=submitted_code,
        )

        return {
            "execution_status": exec_result.status,
            "score": score,
            "passed": passed,
            "public_results": {
                "passed_count": public_passed,
                "total_count": public_total,
                "tests": public_results,
            },
            "hidden_results": {
                "passed_count": hidden_passed,
                "total_count": hidden_total,
                # Summary counts only; no raw inputs leaked
            },
            "rubric_feedback": rubric_feedback,
            "execution_metrics": {
                "duration_ms": exec_result.duration_ms,
                "sandbox_backend": exec_result.sandbox_backend,
                "isolation_guarantees": exec_result.isolation_guarantees,
                "error_message": exec_result.error_message,
            },
        }

    @staticmethod
    def _calculate_rubric(
        score: float,
        public_passed: int,
        public_total: int,
        hidden_passed: int,
        hidden_total: int,
        exec_result: ExecutionResult,
        submitted_code: str,
    ) -> dict[str, Any]:
        """Compute rubric breakdown with clear explanations."""
        correctness_pct = (public_passed / max(1, public_total)) * 100.0
        edge_case_pct = (hidden_passed / max(1, hidden_total)) * 100.0

        # Code quality heuristic via AST
        has_docstring = False
        has_type_hints = False
        try:
            tree = ast.parse(submitted_code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if ast.get_docstring(node):
                        has_docstring = True
                    if node.returns or any(a.annotation for a in node.args.args):
                        has_type_hints = True
        except Exception:
            pass

        quality_score = 70.0
        if has_docstring:
            quality_score += 15.0
        if has_type_hints:
            quality_score += 15.0

        criteria = [
            {
                "criterion": "Objective Correctness",
                "weight": 40,
                "score_percentage": round(correctness_pct, 1),
                "feedback": f"Passed {public_passed}/{public_total} public verification tests.",
            },
            {
                "criterion": "Edge-Case & Boundary Handling",
                "weight": 30,
                "score_percentage": round(edge_case_pct, 1),
                "feedback": f"Handled {hidden_passed}/{hidden_total} hidden edge-case scenarios.",
            },
            {
                "criterion": "Code Quality & Modularity",
                "weight": 20,
                "score_percentage": min(100.0, quality_score),
                "feedback": (
                    "Clean structure with docstrings and type annotations."
                    if (has_docstring and has_type_hints)
                    else "Functional implementation; adding type annotations and docstrings recommended."
                ),
            },
            {
                "criterion": "Runtime Efficiency",
                "weight": 10,
                "score_percentage": 100.0 if exec_result.duration_ms < 500 else 80.0,
                "feedback": f"Execution finished in {exec_result.duration_ms} ms within timeout threshold.",
            },
        ]

        return {
            "overall_rubric_score": score,
            "criteria": criteria,
            "summary_verdict": (
                "Demonstrated verified practical competency."
                if score >= PASSING_SCORE_THRESHOLD
                else "Assessment did not meet the 70% passing threshold. Please review the failed cases and retry."
            ),
        }


assessment_evaluator = AssessmentEvaluator()
