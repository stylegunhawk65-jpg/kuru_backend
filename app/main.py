"""FastAPI application entry point, lifecycle management, and middleware."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.db.session import check_db_connectivity, close_db_engine

from app.services.observability import setup_langsmith_environment
from app.services.scheduler import notification_scheduler

logger = logging.getLogger("kuru.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager for startup and shutdown events."""
    # Startup actions
    setup_logging(log_level=settings.LOG_LEVEL)
    setup_langsmith_environment()
    logger.info(
        "Starting %s v%s [Environment: %s, Debug: %s]",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
        settings.DEBUG,
    )

    # Check database status on startup (non-fatal if disconnected)
    db_status = await check_db_connectivity()
    if db_status.get("status") == "connected":
        logger.info(
            "Database connectivity verified (latency: %sms)",
            db_status.get("latency_ms"),
        )
        try:
            import app.models
            from app.db.base import Base
            from app.db.session import engine, async_session_factory
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema verified and tables ready.")

            # Auto-seed curated Indian tech jobs if empty
            from app.models.job import JobPosting
            from app.services.job_sources.aggregator import job_source_manager
            from sqlalchemy import select, func
            async with async_session_factory() as session:
                count_stmt = select(func.count()).select_from(JobPosting)
                count = (await session.execute(count_stmt)).scalar() or 0
                if count == 0:
                    logger.info("Job listings table is empty; syncing curated India jobs...")
                    await job_source_manager.ensure_job_sources_registered(session)
                    await job_source_manager.sync_source(session, "curated_india")
                    logger.info("Curated India jobs synced successfully.")
        except Exception as exc:
            logger.warning("Error during table initialization or job seeding: %s", exc)
    else:
        logger.warning(
            "Database is unreachable on startup: %s. Continuing in degraded mode.",
            db_status.get("message"),
        )

    # Start background scheduler unless running in testing environment
    if settings.ENVIRONMENT != "testing":
        await notification_scheduler.start()

    yield

    # Shutdown actions
    if settings.ENVIRONMENT != "testing":
        await notification_scheduler.stop()

    logger.info("Shutting down %s", settings.PROJECT_NAME)
    await close_db_engine()


def create_app() -> FastAPI:
    """Application factory for configuring and instantiating the FastAPI app."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="AI-powered Career Twin backend for students in the Indian job and internship market.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS middleware
    # Use explicit origins from configuration; never unrestricted in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register centralized exception handlers
    register_exception_handlers(app, debug=settings.DEBUG)

    # Include versioned API routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get(
        "/",
        summary="Root Index",
        description="Application status and API discovery links.",
        tags=["General"],
    )
    async def root_index() -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Welcome to {settings.PROJECT_NAME}",
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "docs": "/docs",
                "redoc": "/redoc",
                "health": f"{settings.API_V1_STR}/health",
            },
        )

    return app


app = create_app()
