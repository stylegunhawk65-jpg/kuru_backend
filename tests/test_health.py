"""Tests for health check and root endpoints."""

from unittest.mock import patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_index_endpoint(async_client: AsyncClient):
    """Test the root index returns application metadata and discovery URLs."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome to Kuru Backend" in data["message"]
    assert data["version"] == "0.1.0"
    assert data["environment"] == "testing"
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_health_endpoint_healthy(async_client: AsyncClient):
    """Test health endpoint reports healthy status when database is reachable."""
    with patch(
        "app.api.v1.endpoints.health.check_db_connectivity",
        return_value={
            "status": "connected",
            "latency_ms": 1.25,
            "message": "Database is operational",
        },
    ):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["environment"] == "testing"
        assert data["project_name"] == "Kuru Backend"
        assert data["database"]["status"] == "connected"
        assert data["database"]["latency_ms"] == 1.25


@pytest.mark.asyncio
async def test_health_endpoint_degraded(async_client: AsyncClient):
    """Test health endpoint reports degraded status when database is unreachable."""
    with patch(
        "app.api.v1.endpoints.health.check_db_connectivity",
        return_value={
            "status": "disconnected",
            "latency_ms": 10.5,
            "message": "Database is unreachable",
        },
    ):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"]["status"] == "disconnected"
        assert "unreachable" in data["database"]["message"]
