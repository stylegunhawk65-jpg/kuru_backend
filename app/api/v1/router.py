"""API v1 router registry."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    agents,
    applications,
    assessments,
    career_twin,
    firestore_sync,
    github,
    growth,
    health,
    intelligence,
    jobs,
    llm,
    notifications,
    profiles,
    reminders,
    resumes,
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
api_router.include_router(career_twin.router, prefix="/career-twin", tags=["Career Twin"])
api_router.include_router(growth.router, prefix="/growth", tags=["Growth"])
api_router.include_router(llm.router, prefix="/ai", tags=["AI & Career Twin Tasks"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(firestore_sync.router, prefix="/sync", tags=["Firestore Sync"])
api_router.include_router(skillproof.router, prefix="/skillproof", tags=["SkillProof Engine"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Practical Assessments"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])



