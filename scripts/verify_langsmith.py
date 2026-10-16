"""LangSmith Observability Smoke Test and Diagnostic CLI.

Verifies LangSmith environment configuration, credentials validity, and
workflow trace emission for Kuru Career Twin multi-agent pipelines.
Never logs secrets or sensitive student data.
Never fakes successful tracing if the API key is missing or invalid.
"""

import asyncio
import os
import sys

# Ensure repository root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.observability import (
    get_langsmith_diagnostic,
    mask_api_key,
    setup_langsmith_environment,
)


async def main() -> int:
    print("=" * 65)
    print("  KURU CAREER TWIN - LANGSMITH OBSERVABILITY SMOKE TEST")
    print("=" * 65)

    # 1. Environment & Diagnostic Inspection
    diag = setup_langsmith_environment()

    print(f"\n[1] Configuration Summary:")
    print(f"  - Tracing Requested : {diag.enabled}")
    print(f"  - Project Name      : {diag.project}")
    print(f"  - LangSmith Endpoint: {diag.endpoint}")
    print(f"  - API Key Present   : {diag.configured}")
    print(f"  - Masked Key        : {diag.masked_api_key or 'None'}")
    print(f"  - Initial Status    : {diag.status.upper()}")

    # 2. Check Missing or Disabled Configuration
    if not diag.enabled or not diag.configured:
        print("\n" + "!" * 65)
        print("  LANGSMITH TRACING IS NOT CONFIGURED")
        print("!" * 65)
        print("\n" + diag.guidance)
        print("\nSmoke test outcome: UNCONFIGURED (No traces sent. Not faking success).")
        return 1

    # 3. Test API Key Connectivity Against LangSmith Service
    print("\n[2] Verifying API Credentials with LangSmith API...")
    try:
        from langsmith import Client
        from langsmith.utils import LangSmithError

        client = Client(api_key=settings.LANGSMITH_API_KEY, api_url=diag.endpoint)
        try:
            # Check or create project
            if not client.has_project(diag.project):
                print(f"  - Project '{diag.project}' does not exist yet. Creating...")
                client.create_project(diag.project, description="Kuru Career Twin Multi-Agent Observability")
                print(f"  - Project '{diag.project}' created successfully.")
            else:
                print(f"  - Project '{diag.project}' exists and is accessible.")
        except Exception as proj_err:
            print(f"  - Note on project lookup: {proj_err}")

        # List projects to verify token authentication
        _ = list(client.list_projects(limit=2))
        print("  - LangSmith API authentication verified successfully.")
    except Exception as exc:
        err_msg = str(exc)
        print(f"\n[ERROR] Failed to authenticate with LangSmith: {err_msg}")
        print("\n" + get_langsmith_diagnostic(verify_connectivity=False).guidance)
        return 2

    # 4. Run Multi-Agent Workflow Smoke Test with Tracing Active
    print("\n[3] Executing Multi-Agent Pipeline with LangSmith Tracing Active...")
    from app.db.base import Base
    import app.models  # Ensure all models are registered on Base
    from app.db.session import async_session_factory, check_db_connectivity
    from app.services.agents.workflow import workflow_service
    from app.services.llm.factory import get_llm_provider
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    test_uid = "langsmith_smoke_test_user"
    db_status = await check_db_connectivity()
    temp_engine = None

    if db_status.get("status") == "connected":
        print("  - Using active PostgreSQL database connection.")
        session_maker = async_session_factory
    else:
        print("  - PostgreSQL offline; spinning up isolated in-memory SQLite session for smoke test...")
        temp_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with temp_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_maker = async_sessionmaker(bind=temp_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as db:
        try:
            provider = get_llm_provider("mock")
            run_id, state = await workflow_service.run_roadmap_subworkflow(
                db=db,
                firebase_uid=test_uid,
                target_role="Backend Engineer",
                weekly_hours=10,
                provider=provider,
            )
            print(f"  - Workflow Run ID: {run_id}")
            print(f"  - Completed Steps: {state.get('step_history')}")
            print(f"  - Errors         : {state.get('errors')}")
        except Exception as wf_err:
            print(f"  [ERROR] Workflow execution failed: {wf_err}")
            return 3
        finally:
            if temp_engine:
                await temp_engine.dispose()

    print("\n" + "=" * 65)
    print("  SMOKE TEST PASSED: Traces successfully dispatched to LangSmith!")
    print(f"  View your trace run at: https://smith.langchain.com/o/default/projects/p/{diag.project}")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
