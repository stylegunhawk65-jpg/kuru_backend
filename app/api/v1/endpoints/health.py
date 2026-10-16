"""Health check endpoint."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import check_db_connectivity

router = APIRouter()


class DatabaseHealth(BaseModel):
    """Database connectivity health status."""

    status: str
    latency_ms: float | None = None
    message: str


class HealthResponse(BaseModel):
    """Application health response schema."""

    status: str
    environment: str
    version: str
    project_name: str
    database: DatabaseHealth


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Status",
    description="Returns backend service liveness, environment metadata, and database readiness.",
)
async def get_health() -> HealthResponse:
    """Check backend operational health and database connectivity."""
    db_health_data = await check_db_connectivity()

    overall_status = (
        "healthy" if db_health_data.get("status") == "connected" else "degraded"
    )

    return HealthResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        project_name=settings.PROJECT_NAME,
        database=DatabaseHealth(**db_health_data),
    )
