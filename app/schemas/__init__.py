"""API validation schemas package."""

from app.schemas.profile import (
    EducationEntry,
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)

__all__ = [
    "EducationEntry",
    "StudentProfileCreate",
    "StudentProfileUpdate",
    "StudentProfileResponse",
]
