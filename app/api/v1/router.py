"""API v1 router registry."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    agents,
    firestore_sync,
    github,
    health,
    intelligence,
    jobs,
    llm,
    profiles,
    skillproof,
    skills,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
api_router.include_router(github.router, prefix="/github", tags=["GitHub"])
api_router.include_router(skills.router, prefix="/skills", tags=["Skills"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(intelligence.router, prefix="/intelligence", tags=["Intelligence"])
api_router.include_router(llm.router, prefix="/ai", tags=["AI & Career Twin Tasks"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(firestore_sync.router, prefix="/sync", tags=["Firestore Sync"])
api_router.include_router(skillproof.router, prefix="/skillproof", tags=["SkillProof Engine"])


