"""API v1 router registry."""

from fastapi import APIRouter
from app.api.v1.endpoints import health, profiles

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
