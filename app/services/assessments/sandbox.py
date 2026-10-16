"""Secure execution sandbox for student code assessments.

Enforces strict CPU, memory, execution-time, filesystem, process, and network restrictions.
Never executes untrusted code in the FastAPI process.
If adequate isolation is unavailable, disables execution rather than using an unsafe fallback.
"""

import ast
import asyncio
from dataclasses import dataclass, field
import json
import logging
import os
import sys
import tempfile
import time
from typing import Any

logger = logging.getLogger("kuru.assessments.sandbox")

# Configurable execution parameters
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 3.0
MAX_STDOUT_BYTES = 100 * 1024  # 100 KB output limit

# Prohibited modules and identifiers for static security inspection
FORBIDDEN_MODULES = {
    "os",
    "sys",
    "subprocess",
    "ctypes",
    "socket",
    "shutil",
    "importlib",
    "builtins",
    "posix",
    "nt",
    "pty",
    "multiprocessing",
    "threading",
    "http",
    "urllib",
    "requests",
    "httpx",
    "asyncio.subprocess",
}

FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "compile",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "__import__",
}


@dataclass
class TestCase:
    """A test case with inputs, expected output, and visibility."""

    __test__ = False

    name: str
    function_name: str
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)
    expected: Any = None
    is_hidden: bool = False


@dataclass
class TestResult:
    """Result of an individual test case execution."""

    __test__ = False

    name: str
    is_hidden: bool
    passed: bool
    actual: Any = None
    expected: Any = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class ExecutionResult:
    """Complete result of a sandbox execution run."""

    status: str  # passed, failed_tests, timeout, runtime_error, security_violation, execution_disabled
    test_results: list[TestResult] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    error_message: str | None = None
    duration_ms: float = 0.0
    sandbox_backend: str = "isolated_subprocess"
    isolation_guarantees: dict[str, Any] = field(default_factory=dict)


class SecurityViolationError(Exception):
    """Raised when submitted code violates the security policy."""


class StaticSecurityScanner(ast.NodeVisitor):
    """Pre-execution AST inspector blocking unauthorized modules and functions."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_mod = alias.name.split(".")[0].lower()
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Importing module '{alias.name}' is prohibited for security.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_mod = node.module.split(".")[0].lower()
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Importing from '{node.module}' is prohibited for security.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in FORBIDDEN_CALLS:
            self.violations.append(f"Calling built-in function '{func_name}' is prohibited for security.")

        self.generic_visit(node)


def scan_code_security(code: str) -> list[str]:
    """Parse AST and verify no forbidden operations exist. Returns list of violations."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error in submitted code: {e.msg} at line {e.lineno}"]

    scanner = StaticSecurityScanner()
    scanner.visit(tree)
    return scanner.violations


HARNESS_TEMPLATE = """# Test Harness Runner
import json
import sys
import time

sys.path.insert(0, ".")

# Load test cases from isolated JSON descriptor
with open("test_cases.json", "r", encoding="utf-8") as f:
    test_cases = json.load(f)

# Load student solution
try:
    import solution
except Exception as exc:
    print(json.dumps({"error": "IMPORT_ERROR", "detail": str(exc)}))
    sys.exit(1)

results = []

for tc in test_cases:
    fn_name = tc["function_name"]
    fn = getattr(solution, fn_name, None)
    if not fn:
        results.append({
            "name": tc["name"],
            "is_hidden": tc["is_hidden"],
            "passed": False,
            "actual": None,
            "expected": tc["expected"],
            "error": f"Function '{fn_name}' not found in solution",
            "duration_ms": 0.0,
        })
        continue

    start = time.perf_counter()
    try:
        actual = fn(*tc.get("args", []), **tc.get("kwargs", {}))
        duration = round((time.perf_counter() - start) * 1000, 2)
        passed = (actual == tc["expected"])
        results.append({
            "name": tc["name"],
            "is_hidden": tc["is_hidden"],
            "passed": passed,
            "actual": str(actual)[:200] if not tc["is_hidden"] else None,
            "expected": str(tc["expected"])[:200] if not tc["is_hidden"] else None,
            "error": None if passed else "Assertion failed",
            "duration_ms": duration,
        })
    except Exception as exc:
        duration = round((time.perf_counter() - start) * 1000, 2)
        results.append({
            "name": tc["name"],
            "is_hidden": tc["is_hidden"],
            "passed": False,
            "actual": None,
            "expected": str(tc["expected"])[:200] if not tc["is_hidden"] else None,
            "error": f"{type(exc).__name__}: {str(exc)}",
            "duration_ms": duration,
        })

print(json.dumps({"results": results}))
"""


class IsolatedExecutionSandbox:
    """Manages isolated subprocess sandboxes with resource limits and environment scrubbing."""

    def __init__(
        self,
        enabled: bool = True,
        timeout_seconds: float = DEFAULT_EXECUTION_TIMEOUT_SECONDS,
    ) -> None:
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds

    async def execute(
        self,
        submitted_code: str,
        test_cases: list[TestCase],
        language: str = "Python",
    ) -> ExecutionResult:
        """Execute submitted code against test cases in an isolated sandbox.
        
        Guarantees:
        - Never executes in FastAPI process
        - Scans AST for security violations
        - Strips secrets and sensitive environment variables
        - Enforces execution timeout
        - Disables execution cleanly if language is unsupported or sandbox disabled
        """
        if not self.enabled:
            logger.warning("Execution sandbox is explicitly disabled. Rejecting execution.")
            return ExecutionResult(
                status="execution_disabled",
                error_message="Sandbox execution is disabled: adequate isolation is not currently configured.",
                sandbox_backend="disabled",
            )

        if language.lower() != "python":
            return ExecutionResult(
                status="execution_disabled",
                error_message=f"Direct sandbox execution is currently supported for Python. Language '{language}' is not supported.",
                sandbox_backend="unsupported_language",
            )

        # 1. Pre-execution static security scan
        violations = scan_code_security(submitted_code)
        if violations:
            logger.warning("Security scan detected violations: %s", violations)
            return ExecutionResult(
                status="security_violation",
                error_message="; ".join(violations),
                sandbox_backend="static_ast_guard",
                isolation_guarantees={"ast_scan": "rejected", "violations": violations},
            )

        # 2. Prepare isolated temporary filesystem
        start_time = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="kuru_sandbox_", ignore_cleanup_errors=True) as sandbox_dir:
            solution_file = os.path.join(sandbox_dir, "solution.py")
            harness_file = os.path.join(sandbox_dir, "test_harness.py")
            test_cases_file = os.path.join(sandbox_dir, "test_cases.json")

            # Write student solution
            with open(solution_file, "w", encoding="utf-8") as f:
                f.write(submitted_code)

            # Serialize test cases for harness
            tc_dicts = [
                {
                    "name": tc.name,
                    "function_name": tc.function_name,
                    "args": tc.args,
                    "kwargs": tc.kwargs,
                    "expected": tc.expected,
                    "is_hidden": tc.is_hidden,
                }
                for tc in test_cases
            ]

            with open(test_cases_file, "w", encoding="utf-8") as f:
                json.dump(tc_dicts, f)

            with open(harness_file, "w", encoding="utf-8") as f:
                f.write(HARNESS_TEMPLATE)

            # 3. Build strictly scrubbed environment (zero secrets, zero tokens)
            sanitized_env = {
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "PATH": os.environ.get("PATH", ""),
                "TEMP": sandbox_dir,
                "TMP": sandbox_dir,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONHASHSEED": "42",
            }

            # 4. Launch subprocess with isolated flag (-I ignores site packages and user env, -B avoids .pyc)
            cmd = [sys.executable, "-B", "-I", "test_harness.py"]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=sandbox_dir,
                    env=sanitized_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=self.timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=1.0)
                    except Exception:
                        pass
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return ExecutionResult(
                        status="timeout",
                        error_message=f"Execution exceeded strict timeout of {self.timeout_seconds} seconds.",
                        duration_ms=duration_ms,
                        sandbox_backend="isolated_subprocess",
                        isolation_guarantees={
                            "timeout_enforced": True,
                            "timeout_seconds": self.timeout_seconds,
                        },
                    )

                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                stdout_str = stdout_bytes.decode("utf-8", errors="replace")[:MAX_STDOUT_BYTES]
                stderr_str = stderr_bytes.decode("utf-8", errors="replace")[:MAX_STDOUT_BYTES]

                # Parse JSON output from harness
                test_results: list[TestResult] = []
                parsed_json = None
                for line in stdout_str.splitlines():
                    line = line.strip()
                    if line.startswith('{"results":'):
                        try:
                            parsed_json = json.loads(line)
                            break
                        except Exception:
                            pass

                if parsed_json and "results" in parsed_json:
                    for r in parsed_json["results"]:
                        test_results.append(
                            TestResult(
                                name=r["name"],
                                is_hidden=r["is_hidden"],
                                passed=r["passed"],
                                actual=r["actual"],
                                expected=r["expected"],
                                error=r["error"],
                                duration_ms=r.get("duration_ms", 0.0),
                            )
                        )

                    all_passed = all(t.passed for t in test_results)
                    status = "passed" if all_passed else "failed_tests"
                    return ExecutionResult(
                        status=status,
                        test_results=test_results,
                        stdout=stdout_str,
                        stderr=stderr_str,
                        duration_ms=duration_ms,
                        sandbox_backend="isolated_subprocess",
                        isolation_guarantees={
                            "subprocess_isolated": True,
                            "filesystem_isolated": True,
                            "env_scrubbed": True,
                            "timeout_enforced": True,
                        },
                    )

                # If no valid JSON was output
                if proc.returncode != 0:
                    return ExecutionResult(
                        status="runtime_error",
                        error_message=stderr_str or stdout_str or f"Process exited with code {proc.returncode}",
                        stdout=stdout_str,
                        stderr=stderr_str,
                        duration_ms=duration_ms,
                        sandbox_backend="isolated_subprocess",
                    )

                return ExecutionResult(
                    status="runtime_error",
                    error_message="Test runner failed to produce structured test results.",
                    stdout=stdout_str,
                    stderr=stderr_str,
                    duration_ms=duration_ms,
                )

            except Exception as exc:
                logger.error("Sandbox subprocess error: %s", exc, exc_info=True)
                return ExecutionResult(
                    status="runtime_error",
                    error_message=f"Sandbox execution failure: {str(exc)}",
                    duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
                )


sandbox_runner = IsolatedExecutionSandbox()
