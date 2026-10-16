"""Career Profile Agent — Consolidates student profile, target roles, and career interests."""

import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import StudentProfile
from app.schemas.agents import ConsolidatedProfile

logger = logging.getLogger("kuru.agents.profile")


class CareerProfileAgent:
    """Agent responsible for reading, consolidating, and structuring the student's profile."""

    name = "career_profile_agent"

    @classmethod
    async def run(
        cls,
        db: AsyncSession,
        firebase_uid: str,
        target_role_override: str | None = None,
    ) -> ConsolidatedProfile:
        """Fetch and consolidate student profile from database, applying role override if specified."""
        logger.info("CareerProfileAgent running for user '%s'...", firebase_uid)

        stmt = select(StudentProfile).where(StudentProfile.firebase_uid == firebase_uid)
        result = await db.execute(stmt)
        profile_row = result.scalars().first()

        if profile_row:
            target_roles = list(profile_row.target_roles or [])
            primary_role = target_role_override or (target_roles[0] if target_roles else "Software Engineer")
            if primary_role not in target_roles:
                target_roles.insert(0, primary_role)

            edu_list = profile_row.education or []
            first_edu = (
                edu_list[0]
                if (isinstance(edu_list, list) and len(edu_list) > 0 and isinstance(edu_list[0], dict))
                else {}
            )

            return ConsolidatedProfile(
                firebase_uid=firebase_uid,
                full_name=profile_row.full_name,
                target_roles=target_roles,
                primary_target_role=primary_role,
                preferred_locations=list(profile_row.preferred_locations or []),
                interests=list(profile_row.interests or []),
                graduation_year=first_edu.get("graduation_year"),
                degree=first_edu.get("degree"),
                institution=first_edu.get("institution"),
            )

        # Clean fallback if user has not yet initialized a full profile
        primary_role = target_role_override or "Backend Engineer"
        return ConsolidatedProfile(
            firebase_uid=firebase_uid,
            full_name=None,
            target_roles=[primary_role],
            primary_target_role=primary_role,
            preferred_locations=["India", "Remote"],
            interests=["Backend Development", "System Design"],
            graduation_year=None,
            degree=None,
            institution=None,
        )


career_profile_agent = CareerProfileAgent()
