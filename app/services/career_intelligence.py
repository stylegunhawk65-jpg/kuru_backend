"""Career Intelligence Service: Explainable skill-gap analysis, recommendations, and what-if simulations."""

from datetime import datetime, timezone
import logging
import re
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import CareerAssessment
from app.models.job import JobPosting
from app.models.profile import StudentProfile
from app.models.skill import SkillGraphEdge, StudentSkill
from app.schemas.intelligence import (
    CareerPathCompareResponse,
    CareerPathItem,
    MatchedSkillItem,
    MissingSkillItem,
    PrioritizedGapItem,
    SkillGapReportResponse,
    SkillRecommendationItem,
    WhatIfSimulationResponse,
)
from app.services.analyzer import SKILL_TAXONOMY
from app.services.matcher import calculate_job_match, normalize_skill

logger = logging.getLogger("kuru.intelligence")


class CareerIntelligenceService:
    """Deterministic and explainable career readiness, gap analysis, and simulation engine."""

    @staticmethod
    def _get_readiness_level(score: float) -> str:
        """Categorize readiness score into human-friendly milestone tiers."""
        if score >= 80.0:
            return "Ready"
        elif score >= 65.0:
            return "High"
        elif score >= 45.0:
            return "Moderate"
        elif score >= 25.0:
            return "Developing"
        return "Early"

    @staticmethod
    def _filter_jobs_for_role(
        jobs: list[JobPosting],
        target_role: str,
        profile: StudentProfile | None,
    ) -> list[JobPosting]:
        """Filter active jobs to those matching the evaluated role."""
        if not jobs:
            return []

        norm_role = target_role.strip().lower()
        if norm_role != "overall":
            # Match role keywords against title and description
            role_tokens = [t for t in re.findall(r"\w+", norm_role) if len(t) > 2]
            matched = [
                j for j in jobs
                if any(t in j.title.lower() for t in role_tokens)
            ]
            if matched:
                return matched

        # If overall and profile has target roles
        if profile and profile.target_roles:
            all_target_tokens = set()
            for r in profile.target_roles:
                all_target_tokens.update(
                    [t for t in re.findall(r"\w+", r.lower()) if len(t) > 2]
                )
            matched = [
                j for j in jobs
                if any(t in j.title.lower() for t in all_target_tokens)
            ]
            if matched:
                return matched

        # Fallback to all active jobs
        return jobs

    def analyze_skill_gaps(
        self,
        profile: StudentProfile | None,
        skills: list[StudentSkill],
        edges: list[SkillGraphEdge],
        jobs: list[JobPosting],
        target_role: str = "overall",
    ) -> dict[str, Any]:
        """Compute comprehensive, explainable skill gaps, fit score, and recommendations."""
        selected_jobs = self._filter_jobs_for_role(jobs, target_role, profile)
        assessed_jobs_count = len(selected_jobs)

        # 1. Evaluate job match scores
        job_match_results = []
        for job in selected_jobs:
            res = calculate_job_match(job, profile, skills)
            job_match_results.append((job, res))

        if job_match_results:
            overall_fit_score = round(
                sum(res.match_score for _, res in job_match_results) / len(job_match_results),
                1,
            )
        else:
            overall_fit_score = 0.0

        readiness_level = self._get_readiness_level(overall_fit_score)

        # 2. Compile Matched Skills from user skills
        user_skills_norm_map: dict[str, StudentSkill] = {
            normalize_skill(s.skill_name): s for s in skills
        }

        matched_skills_dict: dict[str, MatchedSkillItem] = {}
        for s in skills:
            matched_skills_dict[s.skill_name] = MatchedSkillItem(
                skill_name=s.skill_name,
                category=s.category,
                confidence_score=round(s.confidence_score, 2),
                evidence_count=len(s.evidence or []),
                source_repositories=s.source_repositories or [],
            )

        # 3. Aggregate Missing Skills across selected jobs
        missing_skills_counter: dict[str, int] = {}
        for _, res in job_match_results:
            for missing in res.missing_skills:
                norm_m = normalize_skill(missing)
                # Ensure user truly does not have this skill
                if norm_m not in user_skills_norm_map:
                    missing_skills_counter[missing] = missing_skills_counter.get(missing, 0) + 1

        missing_skill_items: list[MissingSkillItem] = []
        for skill_name, count in missing_skills_counter.items():
            demand_pct = (
                round((count / assessed_jobs_count) * 100, 1)
                if assessed_jobs_count > 0
                else 0.0
            )
            importance = "Beneficial"
            if demand_pct >= 50.0:
                importance = "Critical"
            elif demand_pct >= 25.0:
                importance = "Important"

            missing_skill_items.append(
                MissingSkillItem(
                    skill_name=skill_name,
                    demand_count=count,
                    demand_pct=demand_pct,
                    importance=importance,
                )
            )

        # Sort missing skills by demand count descending
        missing_skill_items.sort(key=lambda item: item.demand_count, reverse=True)

        # 4. Prioritize Skill Gaps using Phase 3 Skill Graph and Student Profile
        # Build graph lookup for user's verified skills
        graph_synergy_map: dict[str, tuple[str, str]] = {}  # norm_missing -> (user_skill, rel_type)
        for edge in edges:
            src_norm = normalize_skill(edge.source_skill)
            tgt_norm = normalize_skill(edge.target_skill)
            if src_norm in user_skills_norm_map and tgt_norm not in user_skills_norm_map:
                graph_synergy_map[tgt_norm] = (edge.source_skill, edge.relationship_type)
            elif tgt_norm in user_skills_norm_map and src_norm not in user_skills_norm_map:
                graph_synergy_map[src_norm] = (edge.target_skill, edge.relationship_type)

        # Fallback to static SKILL_TAXONOMY taxonomy if edge not in user graph
        for skill_name, meta in SKILL_TAXONOMY.items():
            norm_k = normalize_skill(skill_name)
            if norm_k not in user_skills_norm_map:
                for rel_skill, rel_type, _ in meta.get("related", []):
                    rel_norm = normalize_skill(rel_skill)
                    if rel_norm in user_skills_norm_map and norm_k not in graph_synergy_map:
                        graph_synergy_map[norm_k] = (rel_skill, rel_type)

        # Check interest alignment
        user_interests = [i.lower() for i in (profile.interests if profile else [])]

        prioritized_gaps: list[PrioritizedGapItem] = []
        gap_scores: list[tuple[float, str, float, str, list[str]]] = []

        for item in missing_skill_items:
            norm_name = normalize_skill(item.skill_name)
            reasons: list[str] = []

            # A. Demand Score (0-100)
            demand_score = min(100.0, item.demand_pct * 1.5)
            reasons.append(
                f"Required by {item.demand_count}/{assessed_jobs_count} "
                f"({item.demand_pct}%) of analyzed jobs."
            )

            # B. Graph Proximity Score (20-100)
            graph_score = 20.0
            graph_proximity = "Independent"
            if norm_name in graph_synergy_map:
                connected_skill, rel_type = graph_synergy_map[norm_name]
                graph_score = 100.0
                graph_proximity = f"1-Hop Synergy ({connected_skill})"
                reasons.append(
                    f"High learning synergy: connected to your verified '{connected_skill}' "
                    f"skills via '{rel_type}' in the knowledge graph."
                )
            else:
                # Check if same category as any verified skill
                known_cat = SKILL_TAXONOMY.get(item.skill_name, {}).get("category")
                if known_cat and any(s.category == known_cat for s in skills):
                    graph_score = 50.0
                    graph_proximity = f"Same Category ({known_cat})"
                    reasons.append(f"Shares ecosystem category ({known_cat}) with your verified skills.")

            # C. Interest Score (0 or 100)
            interest_score = 0.0
            matched_interest = next((i for i in user_interests if i in item.skill_name.lower() or item.skill_name.lower() in i), None)
            if matched_interest:
                interest_score = 100.0
                reasons.append(f"Directly aligns with your stated career interest in '{matched_interest.title()}'.")

            # Composite Priority Formula: Demand 50%, Graph 30%, Interest 20%
            priority_score = round(
                (demand_score * 0.50) + (graph_score * 0.30) + (interest_score * 0.20),
                1,
            )
            gap_scores.append((priority_score, item.skill_name, item.demand_pct, graph_proximity, reasons))

        # Sort by priority score descending
        gap_scores.sort(key=lambda x: x[0], reverse=True)

        for rank, (score, s_name, d_pct, prox, r_list) in enumerate(gap_scores, start=1):
            prioritized_gaps.append(
                PrioritizedGapItem(
                    skill_name=s_name,
                    priority_rank=rank,
                    priority_score=score,
                    market_demand_pct=d_pct,
                    graph_proximity=prox,
                    reasons=r_list,
                )
            )

        # 5. Generate Skill Recommendations (Top 5 prioritized gaps)
        recommendations: list[SkillRecommendationItem] = []
        for gap in prioritized_gaps[:5]:
            cat = SKILL_TAXONOMY.get(gap.skill_name, {}).get("category", "Tool/Technology")

            # Count how many currently mismatched jobs require this skill
            unlocked_count = sum(
                1 for j, res in job_match_results
                if gap.skill_name in res.missing_skills
            )

            # Effort estimate based on graph proximity
            if "1-Hop" in gap.graph_proximity:
                effort = "Low (1-2 weeks)"
            elif "Same Category" in gap.graph_proximity:
                effort = "Medium (3-4 weeks)"
            else:
                effort = "High (5-8 weeks)"

            recommendation_reason = (
                f"Mastering '{gap.skill_name}' will unlock {unlocked_count} target job opportunities. "
                + " ".join(gap.reasons)
            )

            recommendations.append(
                SkillRecommendationItem(
                    skill_name=gap.skill_name,
                    category=cat,
                    market_demand_pct=gap.market_demand_pct,
                    unlocked_jobs_count=unlocked_count,
                    effort_estimate=effort,
                    reason=recommendation_reason,
                )
            )

        summary_notes = (
            f"Assessed {assessed_jobs_count} job postings for role '{target_role}'. "
            f"Portfolio readiness is {overall_fit_score}% ({readiness_level}). "
            f"Identified {len(matched_skills_dict)} evidence-backed skills and {len(prioritized_gaps)} prioritized gaps."
        )

        return {
            "target_role": target_role,
            "overall_fit_score": overall_fit_score,
            "readiness_level": readiness_level,
            "assessed_jobs_count": assessed_jobs_count,
            "matched_skills": list(matched_skills_dict.values()),
            "missing_skills": missing_skill_items,
            "prioritized_gaps": prioritized_gaps,
            "recommendations": recommendations,
            "summary_notes": summary_notes,
        }

    def compare_career_paths(
        self,
        profile: StudentProfile | None,
        skills: list[StudentSkill],
        edges: list[SkillGraphEdge],
        jobs: list[JobPosting],
        roles: list[str],
    ) -> CareerPathCompareResponse:
        """Compare candidate career paths and rank readiness deterministically."""
        compared_roles: list[CareerPathItem] = []

        for role in roles:
            norm_role = role.strip().lower()
            role_tokens = [t for t in re.findall(r"\w+", norm_role) if len(t) > 2]
            role_jobs = [
                j for j in jobs
                if any(t in j.title.lower() for t in role_tokens)
            ]
            jobs_to_eval = role_jobs if role_jobs else jobs

            match_results = [calculate_job_match(j, profile, skills) for j in jobs_to_eval]
            readiness_score = (
                round(sum(r.match_score for r in match_results) / len(match_results), 1)
                if match_results
                else 0.0
            )
            readiness_level = self._get_readiness_level(readiness_score)

            # Matched & missing skills
            all_matched: set[str] = set()
            missing_counter: dict[str, int] = {}
            for r in match_results:
                all_matched.update(r.matched_skills)
                for m in r.missing_skills:
                    missing_counter[m] = missing_counter.get(m, 0) + 1

            critical_gaps = [
                k for k, _ in sorted(missing_counter.items(), key=lambda x: x[1], reverse=True)[:3]
            ]

            # Estimated runway weeks based on critical gap count
            runway_weeks = f"{max(2, len(critical_gaps) * 3)} to {max(4, len(critical_gaps) * 5)} weeks"
            assumptions = (
                "Runway estimate assumes 10-15 hours/week of focused project-based learning. "
                "Progress accelerates with existing programming foundations."
            )

            compared_roles.append(
                CareerPathItem(
                    role_name=role,
                    active_jobs_count=len(role_jobs),
                    readiness_score=readiness_score,
                    readiness_level=readiness_level,
                    matched_skills_count=len(all_matched),
                    missing_skills_count=len(missing_counter),
                    top_matched_skills=list(all_matched)[:5],
                    critical_gaps=critical_gaps,
                    estimated_runway_weeks=runway_weeks,
                    assumptions=assumptions,
                )
            )

        # Recommendation: select role with best combination of readiness and market postings
        best_role_item = max(
            compared_roles,
            key=lambda x: (x.readiness_score * 0.7) + (min(x.active_jobs_count, 10) * 3.0),
        )

        recommendation_reason = (
            f"'{best_role_item.role_name}' is currently your strongest career path with a "
            f"readiness score of {best_role_item.readiness_score}% ({best_role_item.readiness_level}) "
            f"and {best_role_item.active_jobs_count} active job listings in the market."
        )

        return CareerPathCompareResponse(
            compared_roles=compared_roles,
            recommended_role=best_role_item.role_name,
            recommendation_reason=recommendation_reason,
        )

    def simulate_what_if(
        self,
        profile: StudentProfile | None,
        skills: list[StudentSkill],
        edges: list[SkillGraphEdge],
        jobs: list[JobPosting],
        hypothetical_skills: list[str],
        target_role: str = "overall",
    ) -> WhatIfSimulationResponse:
        """Simulate portfolio impact of acquiring hypothetical skills."""
        # 1. Baseline assessment
        baseline_analysis = self.analyze_skill_gaps(profile, skills, edges, jobs, target_role)
        baseline_score = baseline_analysis["overall_fit_score"]
        baseline_readiness = baseline_analysis["readiness_level"]

        # 2. Add hypothetical skills
        simulated_skills_list = list(skills)
        user_norm_skills = {normalize_skill(s.skill_name) for s in skills}

        added_skills = []
        for h_skill in hypothetical_skills:
            norm_h = normalize_skill(h_skill)
            if norm_h not in user_norm_skills:
                simulated_skills_list.append(
                    StudentSkill(
                        id=str(uuid.uuid4()),
                        firebase_uid=profile.firebase_uid if profile else "simulated_user",
                        skill_name=h_skill.strip(),
                        category="Simulated",
                        confidence_score=0.85,
                        evidence=[{"type": "simulation", "description": "Hypothetical skill addition"}],
                        source_repositories=["simulation"],
                    )
                )
                added_skills.append(h_skill.strip())
                user_norm_skills.add(norm_h)

        # 3. Simulated assessment
        simulated_analysis = self.analyze_skill_gaps(
            profile, simulated_skills_list, edges, jobs, target_role
        )
        simulated_score = simulated_analysis["overall_fit_score"]
        simulated_readiness = simulated_analysis["readiness_level"]

        score_delta = round(simulated_score - baseline_score, 1)

        # Resolved gaps vs remaining gaps
        baseline_missing_names = {item.skill_name for item in baseline_analysis["missing_skills"]}
        simulated_missing_names = {item.skill_name for item in simulated_analysis["missing_skills"]}

        resolved_gaps = list(baseline_missing_names - simulated_missing_names)
        remaining_gaps = [
            item.skill_name for item in simulated_analysis["prioritized_gaps"][:5]
        ]

        # Count newly unlocked jobs (jobs achieving >= 65% match or gaining >= 15% fit)
        selected_jobs = self._filter_jobs_for_role(jobs, target_role, profile)
        newly_unlocked = 0
        for job in selected_jobs:
            base_m = calculate_job_match(job, profile, skills).match_score
            sim_m = calculate_job_match(job, profile, simulated_skills_list).match_score
            if sim_m >= 65.0 and base_m < 65.0:
                newly_unlocked += 1

        assumptions = (
            "Simulation assumes acquisition of hypothetical skills with 0.85 proficiency confidence. "
            "Actual career fit gains depend on practical code evidence and portfolio validation."
        )

        return WhatIfSimulationResponse(
            target_role=target_role,
            simulated_skills=added_skills,
            baseline_fit_score=baseline_score,
            simulated_fit_score=simulated_score,
            score_delta=score_delta,
            baseline_readiness_level=baseline_readiness,
            simulated_readiness_level=simulated_readiness,
            newly_unlocked_jobs_count=newly_unlocked,
            resolved_gaps=resolved_gaps,
            remaining_gaps=remaining_gaps,
            assumptions=assumptions,
        )

    async def get_or_create_assessment(
        self,
        db: AsyncSession,
        firebase_uid: str,
        target_role: str = "overall",
        force_refresh: bool = False,
    ) -> CareerAssessment:
        """Retrieve existing cached assessment or compute and persist a fresh snapshot."""
        if not force_refresh:
            stmt = select(CareerAssessment).where(
                CareerAssessment.firebase_uid == firebase_uid,
                CareerAssessment.target_role == target_role,
            )
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                return existing

        # Fetch dependencies from DB
        # 1. Profile
        prof_stmt = select(StudentProfile).where(StudentProfile.firebase_uid == firebase_uid)
        profile = (await db.execute(prof_stmt)).scalar_one_or_none()

        # 2. Skills
        skills_stmt = select(StudentSkill).where(StudentSkill.firebase_uid == firebase_uid)
        skills = (await db.execute(skills_stmt)).scalars().all()

        # 3. Edges
        edges_stmt = select(SkillGraphEdge).where(SkillGraphEdge.firebase_uid == firebase_uid)
        edges = (await db.execute(edges_stmt)).scalars().all()

        # 4. Jobs
        jobs_stmt = select(JobPosting).where(JobPosting.is_active == True)
        jobs = (await db.execute(jobs_stmt)).scalars().all()

        # Compute analysis
        analysis = self.analyze_skill_gaps(profile, skills, edges, jobs, target_role)

        # Check if record already exists to update
        stmt = select(CareerAssessment).where(
            CareerAssessment.firebase_uid == firebase_uid,
            CareerAssessment.target_role == target_role,
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        matched_dicts = [m.model_dump() for m in analysis["matched_skills"]]
        missing_dicts = [m.model_dump() for m in analysis["missing_skills"]]
        gap_dicts = [g.model_dump() for g in analysis["prioritized_gaps"]]
        rec_dicts = [r.model_dump() for r in analysis["recommendations"]]

        if record:
            record.overall_fit_score = analysis["overall_fit_score"]
            record.readiness_level = analysis["readiness_level"]
            record.matched_skills = matched_dicts
            record.missing_skills = missing_dicts
            record.prioritized_gaps = gap_dicts
            record.recommendations = rec_dicts
            record.assessed_jobs_count = analysis["assessed_jobs_count"]
            record.summary_notes = analysis["summary_notes"]
            record.updated_at = datetime.now(timezone.utc)
        else:
            record = CareerAssessment(
                id=str(uuid.uuid4()),
                firebase_uid=firebase_uid,
                target_role=target_role,
                overall_fit_score=analysis["overall_fit_score"],
                readiness_level=analysis["readiness_level"],
                matched_skills=matched_dicts,
                missing_skills=missing_dicts,
                prioritized_gaps=gap_dicts,
                recommendations=rec_dicts,
                assessed_jobs_count=analysis["assessed_jobs_count"],
                summary_notes=analysis["summary_notes"],
            )
            db.add(record)

        await db.commit()
        await db.refresh(record)
        return record


career_intelligence_service = CareerIntelligenceService()
