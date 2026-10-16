"""Pydantic validation schemas for Student Career Profiles."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EducationEntry(BaseModel):
    """Academic qualification entry."""

    institution: str = Field(..., min_length=1, max_length=255, description="Institution or university name")
    degree: str = Field(..., min_length=1, max_length=255, description="Degree name (e.g. B.Tech, B.Sc, MCA)")
    field_of_study: str | None = Field(None, max_length=255, description="Major or specialization")
    start_year: int | None = Field(None, ge=1950, le=2100, description="Start year")
    end_year: int | None = Field(None, ge=1950, le=2100, description="Graduation year")
    grade_or_cgpa: str | None = Field(None, max_length=50, description="CGPA or grade")

    model_config = ConfigDict(from_attributes=True)


class StudentProfileCreate(BaseModel):
    """Request schema for creating a new student career profile."""

    full_name: str = Field(..., min_length=1, max_length=255, description="Full student name")
    email: EmailStr | None = Field(None, description="Contact email address")
    education: list[EducationEntry] = Field(default_factory=list, description="Academic qualifications")
    interests: list[str] = Field(default_factory=list, description="Career and technical interests")
    target_roles: list[str] = Field(default_factory=list, description="Target job and internship roles")
    preferred_locations: list[str] = Field(default_factory=list, description="Preferred employment locations")
    bio: str | None = Field(None, max_length=2000, description="Short career bio")


class StudentProfileUpdate(BaseModel):
    """Request schema for updating an existing student career profile."""

    full_name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    education: list[EducationEntry] | None = None
    interests: list[str] | None = None
    target_roles: list[str] | None = None
    preferred_locations: list[str] | None = None
    bio: str | None = Field(None, max_length=2000)


class StudentProfileResponse(BaseModel):
    """Public serialization schema for a student career profile."""

    id: str
    firebase_uid: str
    full_name: str
    email: str | None = None
    education: list[EducationEntry] = []
    interests: list[str] = []
    target_roles: list[str] = []
    preferred_locations: list[str] = []
    bio: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
