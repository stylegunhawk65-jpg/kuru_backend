"""Resource Research Agent — Finds authentic, verified learning resources with genuine documentation URLs."""

import logging
from app.schemas.agents import GenuineResourceItem
from app.services.agents.resource_registry import is_url_genuine, resource_registry

logger = logging.getLogger("kuru.agents.resources")


class ResourceResearchAgent:
    """Agent that queries the verified resource registry for genuine learning links without hallucinations."""

    name = "resource_research_agent"

    @classmethod
    async def run(
        cls,
        skills: list[str],
        limit_per_skill: int = 2,
    ) -> dict[str, list[GenuineResourceItem]]:
        """Look up verified documentation, tutorials, and interactive courses for targeted skills."""
        logger.info("ResourceResearchAgent querying genuine resources for: %s", skills)

        results: dict[str, list[GenuineResourceItem]] = {}

        for skill in skills:
            found = resource_registry.get_resources_for_skill(skill, limit=limit_per_skill)
            valid_items: list[GenuineResourceItem] = []
            for r in found:
                # Rigorous safeguard: ensure URL is genuine and strictly HTTPS
                if is_url_genuine(r.url):
                    valid_items.append(
                        GenuineResourceItem(
                            skill_name=r.skill_name,
                            title=r.title,
                            url=r.url,
                            provider=r.provider,
                            resource_type=r.resource_type,
                            difficulty=r.difficulty,
                            estimated_hours=r.estimated_hours,
                            description=r.description,
                        )
                    )
            results[skill] = valid_items

        return results


resource_research_agent = ResourceResearchAgent()
