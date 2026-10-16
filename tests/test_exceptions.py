"""Tests for exception handlers and error response uniformity."""

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.exceptions import AppException, ResourceNotFoundError
from app.main import create_app

mock_router = APIRouter()


class SamplePayload(BaseModel):
    name: str
    age: int


@mock_router.post("/test-validation")
async def validation_route(payload: SamplePayload):
    return {"name": payload.name, "age": payload.age}


@mock_router.get("/test-custom-app-exception")
async def custom_app_exception_route():
    raise AppException(
        detail="Custom failure condition",
        status_code=400,
        error_code="CUSTOM_FAILURE",
        errors=[{"field": "test", "issue": "failed"}],
    )


@mock_router.get("/test-resource-not-found")
async def resource_not_found_route():
    raise ResourceNotFoundError("CareerProfile", "usr_12345")


@mock_router.get("/test-internal-crash")
async def crash_route():
    raise RuntimeError("Sensitive secret database internal pointer failure")


@pytest.fixture
def error_test_app():
    """Create an app with test error routes and debug=False."""
    app = create_app()
    app.include_router(mock_router)
    return app


@pytest.mark.asyncio
async def test_404_handler_structure(error_test_app):
    """Ensure standard 404 responses conform to unified JSON error schema."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/non-existent-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["error_code"] == "HTTP_404"
        assert data["errors"] == []


@pytest.mark.asyncio
async def test_validation_error_structure(error_test_app):
    """Ensure validation errors conform to unified JSON error schema."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send string instead of int for age, missing name
        response = await client.post("/test-validation", json={"age": "not-an-int"})
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert len(data["errors"]) > 0
        assert any("age" in err["field"] for err in data["errors"])


@pytest.mark.asyncio
async def test_custom_app_exception_handling(error_test_app):
    """Ensure custom AppException subclasses are mapped cleanly."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-custom-app-exception")
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Custom failure condition"
        assert data["error_code"] == "CUSTOM_FAILURE"
        assert data["errors"] == [{"field": "test", "issue": "failed"}]


@pytest.mark.asyncio
async def test_resource_not_found_exception(error_test_app):
    """Ensure ResourceNotFoundError returns 404 with structured code."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-resource-not-found")
        assert response.status_code == 404
        data = response.json()
        assert "CareerProfile with identifier 'usr_12345' was not found" in data["detail"]
        assert data["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_unhandled_exception_does_not_leak_secrets(error_test_app):
    """Ensure internal unhandled exceptions do not leak internal messages when DEBUG=False."""
    transport = ASGITransport(app=error_test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-internal-crash")
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        # In non-debug mode, the raw exception text must not appear
        assert "Sensitive secret" not in data["detail"]
        assert data["detail"] == "An internal server error occurred."
