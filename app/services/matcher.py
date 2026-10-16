"""Transparent baseline rule-based matching engine for jobs and student profiles."""

from dataclasses import dataclass, field
import re
from typing import Any

from app.models.job import JobPosting
from app.models.profile import StudentProfile
from app.models.skill import StudentSkill


def normalize_skill(name: str) -> str:
    """Normalize skill name for robust fuzzy/canonical comparison."""
    norm = re.sub(r"[^a-zA-Z0-9+#]", "", name.lower())
    synonyms = {
        "postgres": "postgresql",
        "psql": "postgresql",
        "nodejs": "node",
        "reactjs": "react",
        "golang": "go",
        "k8s": "kubernetes",
        "ts": "typescript",
        "js": "javascript",
        "py": "python",
        "restapi": "restapis",
        "rest": "restapis",
    }
    return synonyms.get(norm, norm)


@dataclass
class JobMatchResult:
    """Detailed breakdown of matching computation."""

    match_score: float
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    match_reasons: list[str] = field(default_factory=list)


def calculate_job_match(
    job: JobPosting,
    profile: StudentProfile | None,
    skills: list[StudentSkill],
) -> JobMatchResult:
    """Compute transparent, rule-based job alignment score (0.0 to 100.0).

    Formula breakdown:
    - Evidence-backed Skills Match: 50% max
    - Target Role Alignment:        25% max
    - Location Alignment:           15% max
    - Career Interests Alignment:   10% max
    """
    total_score = 0.0
    match_reasons: list[str] = []
    matched_skills: list[str] = []
    missing_skills: list[str] = []

    # Map user's evidence-backed skills: norm_name -> (original_name, confidence)
    user_skills_map: dict[str, tuple[str, float]] = {}
    for s in skills:
        norm = normalize_skill(s.skill_name)
        if norm:
            user_skills_map[norm] = (s.skill_name, float(s.confidence_score))

    # Also consider profile interests as minor skill signals (0.70 baseline confidence)
    if profile and profile.interests:
        for item in profile.interests:
            norm = normalize_skill(item)
            if norm and norm not in user_skills_map:
                user_skills_map[norm] = (item, 0.70)

    # 1. Evidence-backed Skills (50% max)
    required_skills = job.required_skills or []
    if not required_skills:
        skill_score = 25.0
        total_score += skill_score
        match_reasons.append("Listing has no explicit skill requirements; baseline neutral score (+25.0 pts).")
    else:
        skill_weight_per_item = 50.0 / len(required_skills)
        accumulated_skill_score = 0.0

        for req in required_skills:
            norm_req = normalize_skill(req)
            if norm_req in user_skills_map:
                orig_name, conf = user_skills_map[norm_req]
                matched_skills.append(req)
                item_score = skill_weight_per_item * conf
                accumulated_skill_score += item_score
            else:
                missing_skills.append(req)

        total_score += accumulated_skill_score
        pct = int(round((len(matched_skills) / len(required_skills)) * 100))
        match_reasons.append(
            f"Skill match: {len(matched_skills)}/{len(required_skills)} required skills ({pct}%): "
            f"{', '.join(matched_skills) if matched_skills else 'None'} (+{accumulated_skill_score:.1f} pts)."
        )
        demonstrated = [
            s.skill_name for s in skills if getattr(s, "verification_status", None) == "practically_demonstrated"
        ]
        if demonstrated:
            demo_matched = [m for m in matched_skills if any(d.lower() in m.lower() for d in demonstrated)]
            if demo_matched:
                match_reasons.append(f"Practically verified skills demonstrated in code assessment: {', '.join(demo_matched)}.")
        if missing_skills:
            match_reasons.append(f"Missing required skills for role: {', '.join(missing_skills)}.")

    # 2. Target Role Alignment (25% max)
    role_score = 5.0  # baseline if no roles defined
    matched_role = None
    if profile and profile.target_roles:
        job_title_norm = job.title.lower()
        exact_match = False
        partial_match = False

        for target in profile.target_roles:
            target_norm = target.lower()
            # Exact or core substring match (e.g., 'backend developer' in 'Junior Backend Developer')
            if target_norm in job_title_norm:
                exact_match = True
                matched_role = target
                break
            # Token overlap (e.g., 'backend' or 'engineer')
            target_tokens = set(re.findall(r"\w+", target_norm))
            title_tokens = set(re.findall(r"\w+", job_title_norm))
            overlap = target_tokens.intersection(title_tokens)
            # Exclude trivial stop words
            significant_overlap = [w for w in overlap if w not in {"and", "or", "in", "the", "for", "junior", "senior", "lead", "associate"}]
            if significant_overlap:
                partial_match = True
                matched_role = target

        if exact_match:
            role_score = 25.0
            match_reasons.append(f"Target role aligns strongly with '{matched_role}' in job title (+25.0 pts).")
        elif partial_match:
            role_score = 15.0
            match_reasons.append(f"Target role aligns partially with '{matched_role}' (+15.0 pts).")
        else:
            role_score = 5.0
            match_reasons.append(f"Job title '{job.title}' differs from target roles (+5.0 pts baseline).")
    else:
        match_reasons.append("No target roles specified in profile; neutral baseline applied (+5.0 pts).")

    total_score += role_score

    # 3. Location Alignment (15% max)
    location_score = 8.0  # baseline
    if profile and profile.preferred_locations:
        user_locs = [loc.lower().strip() for loc in profile.preferred_locations]
        job_loc_norm = job.location.lower()

        matched_loc = None
        for u_loc in user_locs:
            if u_loc in job_loc_norm:
                matched_loc = u_loc
                break

        if job.is_remote and any("remote" in l for l in user_locs):
            location_score = 15.0
            match_reasons.append("Remote position matches remote work preference (+15.0 pts).")
        elif matched_loc:
            location_score = 15.0
            match_reasons.append(f"Job location '{job.location}' matches preferred location '{matched_loc.title()}' (+15.0 pts).")
        elif job.is_remote:
            location_score = 12.0
            match_reasons.append("Listing is fully remote (+12.0 pts).")
        else:
            location_score = 0.0
            match_reasons.append(f"Job location '{job.location}' outside preferred locations (0.0 pts).")
    else:
        match_reasons.append("No location preferences configured; neutral baseline applied (+8.0 pts).")

    total_score += location_score

    # 4. Career Interests Alignment (10% max)
    interest_score = 3.0  # baseline
    if profile and profile.interests:
        job_text = f"{job.title} {job.description}".lower()
        matched_interests = []
        for interest in profile.interests:
            if interest.lower() in job_text:
                matched_interests.append(interest)

        if matched_interests:
            interest_score = min(10.0, 5.0 * len(matched_interests))
            match_reasons.append(
                f"Job description aligns with stated interests: {', '.join(matched_interests)} (+{interest_score:.1f} pts)."
            )
        else:
            interest_score = 3.0
            match_reasons.append("No explicit match for stated interests (+3.0 pts baseline).")
    else:
        match_reasons.append("No profile interests configured; neutral baseline applied (+3.0 pts).")

    total_score += interest_score

    # Clamp total score between 0.0 and 100.0
    final_score = max(0.0, min(100.0, round(total_score, 1)))

    return JobMatchResult(
        match_score=final_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        match_reasons=match_reasons,
    )
