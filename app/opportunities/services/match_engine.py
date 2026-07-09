import logging
from app.extensions import db
from app.opportunities.models import Opportunity, OpportunityMatchScore

logger = logging.getLogger(__name__)


def calculate_match_score(user_id: int, opportunity_id: int, force: bool = False) -> dict:
    existing = OpportunityMatchScore.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    if existing and not force:
        return _score_to_dict(existing)

    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return {"error": "Opportunity not found"}

    scores = _compute_scores(user_id, opp)

    if existing:
        for field, val in scores.items():
            setattr(existing, field, val)
    else:
        existing = OpportunityMatchScore(
            user_id=user_id, opportunity_id=opportunity_id, **scores
        )
        db.session.add(existing)
    db.session.commit()

    return _score_to_dict(existing)


def calculate_all_matches(user_id: int, opportunity_ids: list[int]) -> list[dict]:
    results = []
    for oid in opportunity_ids:
        try:
            score = calculate_match_score(user_id, oid)
            results.append(score)
        except Exception as e:
            logger.error("Match calculation failed for opportunity %s: %s", oid, e)
    return results


def _compute_scores(user_id: int, opp: Opportunity) -> dict:
    from app.career.services import build_career_memory
    from app.resume.models import Resume
    from app.resume.ats import score_resume as ats_score_resume

    memory = build_career_memory(user_id)
    resume = Resume.query.filter_by(user_id=user_id).first()

    description_text = f"{opp.description or ''}\n{' '.join(opp.requirements or [])}\n{' '.join(opp.responsibilities or [])}"

    ats_result = ats_score_resume(resume, description_text) if resume else None
    ats_match = ats_result["overall_score"] if ats_result and ats_result["overall_score"] is not None else 0

    user_skills = set()
    if resume and resume.skills:
        user_skills = {s.lower().strip() for s in resume.skills if isinstance(s, str)}
    if opp.tech_stack:
        job_skills = {s.lower().strip() for s in opp.tech_stack if isinstance(s, str)}
        matched = user_skills & job_skills
        skill_match = round((len(matched) / len(job_skills)) * 100) if job_skills else 50
    else:
        matched = set()
        skill_match = 50

    resume_match = _calculate_resume_match(memory)

    profile = memory.get("career_profile", {}) or {}
    experience_match = _calculate_experience_match(profile, opp)

    project_match = _calculate_project_match(memory, description_text)

    goal_match = _calculate_goal_match(memory, opp)

    location_match = _calculate_location_match(profile, opp)

    salary_match = _calculate_salary_match(profile, opp)

    scores_dict = {
        "ats_match": ats_match,
        "skill_match": skill_match,
        "resume_match": resume_match,
        "experience_match": experience_match,
        "project_match": project_match,
        "goal_match": goal_match,
        "location_match": location_match,
        "salary_match": salary_match,
    }
    weights = {
        "ats_match": 0.25,
        "skill_match": 0.20,
        "resume_match": 0.15,
        "experience_match": 0.12,
        "project_match": 0.10,
        "goal_match": 0.08,
        "location_match": 0.05,
        "salary_match": 0.05,
    }
    overall_score = round(sum(
        scores_dict[k] * w for k, w in weights.items()
    ))

    explanations = {}
    if ats_match >= 80:
        explanations["ats_match"] = "Your resume aligns well with this job description"
    elif ats_match >= 50:
        explanations["ats_match"] = f"Your resume has {ats_match}% keyword match — add more relevant keywords"
    else:
        explanations["ats_match"] = "Your resume needs significant optimization for this role"

    if skill_match >= 70:
        explanations["skill_match"] = f"You match {len(matched)} of {len(opp.tech_stack or [])} required skills"
    elif skill_match >= 40:
        explanations["skill_match"] = f"You have some required skills ({len(matched)}/{len(opp.tech_stack or [])})"
    else:
        explanations["skill_match"] = "Several required skills missing — check the skill gap analysis"

    explanations["experience_match"] = _explain_experience(profile, opp)
    explanations["project_match"] = project_match >= 50 and "Your projects demonstrate relevant experience" or "Add targeted projects to strengthen your profile"
    explanations["goal_match"] = goal_match >= 50 and f"Matches your career goal: {profile.get('target_role', 'N/A')}" or "Consider whether this fits your career goals"
    explanations["location_match"] = location_match >= 50 and "Location is compatible" or "Location mismatch — consider relocation or remote"
    explanations["salary_match"] = salary_match >= 50 and "Salary range aligns with expectations" or "Salary below expectations"

    return {
        "overall_score": overall_score,
        "ats_match": ats_match,
        "resume_match": resume_match,
        "skill_match": skill_match,
        "experience_match": experience_match,
        "project_match": project_match,
        "goal_match": goal_match,
        "location_match": location_match,
        "salary_match": salary_match,
        "explanation": explanations,
    }


def _calculate_resume_match(memory: dict) -> int:
    resume = memory.get("resume", {}) or {}
    if not resume:
        return 0
    score = 0
    if resume.get("summary"):
        score += 20
    if resume.get("experience") and len(resume.get("experience", [])) > 0:
        score += 25
    if resume.get("education") and len(resume.get("education", [])) > 0:
        score += 15
    if resume.get("skills") and len(resume.get("skills", [])) > 5:
        score += 20
    if resume.get("projects") and len(resume.get("projects", [])) > 0:
        score += 20
    return min(score, 100)


def _calculate_experience_match(profile: dict, opp: Opportunity) -> int:
    user_exp = profile.get("years_experience") or 0
    req_min = opp.experience_required or 0
    req_max = opp.experience_max or 99
    if req_min <= user_exp <= req_max:
        return 100
    if user_exp < req_min:
        return max(0, 100 - (req_min - user_exp) * 20)
    return max(0, 100 - (user_exp - req_max) * 10)


def _calculate_project_match(memory: dict, description_text: str) -> int:
    resume = memory.get("resume", {}) or {}
    projects = resume.get("projects", [])
    if not projects:
        return 0
    proj_text = " ".join(
        f"{p.get('name', '')} {p.get('description', '')} {' '.join(p.get('technologies', []) or [])}"
        for p in projects
    ).lower()
    kw = set(description_text.lower().split())
    matched = sum(1 for w in kw if len(w) > 4 and w in proj_text)
    return min(100, round(matched / max(len(kw) * 0.01, 1)))


def _calculate_goal_match(memory: dict, opp: Opportunity) -> int:
    profile = memory.get("career_profile", {}) or {}
    score = 50
    target_role = (profile.get("target_role") or "").lower()
    if target_role and target_role in (opp.title or "").lower():
        score += 30
    target_company = (profile.get("target_company") or "").lower()
    if target_company and target_company in (opp.company_name or "").lower():
        score += 20
    return min(score, 100)


def _calculate_location_match(profile: dict, opp: Opportunity) -> int:
    if opp.remote_type == "remote":
        return 100
    pref = profile.get("preferred_locations") or []
    if not pref and not profile.get("target_location"):
        return 50
    target = (profile.get("target_location") or "").lower()
    opp_loc = (opp.location or "").lower()
    if target and target in opp_loc:
        return 100
    for loc in pref:
        if isinstance(loc, str) and loc.lower() in opp_loc:
            return 100
    return 30


def _calculate_salary_match(profile: dict, opp: Opportunity) -> int:
    target_salary = profile.get("target_salary") or ""
    if not target_salary or not opp.salary_min:
        return 50
    try:
        target_val = int("".join(c for c in target_salary if c.isdigit()))
        if target_val == 0:
            return 50
        if opp.salary_min >= target_val:
            return 100
        ratio = opp.salary_max / target_val if target_val else 0
        if ratio >= 0.8:
            return 80
        if ratio >= 0.6:
            return 60
        return 30
    except (ValueError, TypeError):
        return 50


def _explain_experience(profile: dict, opp: Opportunity) -> str:
    user_exp = profile.get("years_experience") or 0
    req_min = opp.experience_required or 0
    req_max = opp.experience_max or 99
    if req_min <= user_exp <= req_max:
        return f"Your {user_exp} years matches the {req_min}-{req_max} year range"
    if user_exp < req_min:
        return f"Requires {req_min}+ years, you have {user_exp}"
    return f"You exceed the experience requirement ({user_exp} vs {req_max} max)"


def _score_to_dict(score: OpportunityMatchScore) -> dict:
    return {
        "id": score.id,
        "opportunity_id": score.opportunity_id,
        "overall_score": score.overall_score,
        "ats_match": score.ats_match,
        "resume_match": score.resume_match,
        "skill_match": score.skill_match,
        "experience_match": score.experience_match,
        "project_match": score.project_match,
        "goal_match": score.goal_match,
        "location_match": score.location_match,
        "salary_match": score.salary_match,
        "explanation": score.explanation or {},
        "created_at": score.created_at.isoformat() if score.created_at else None,
    }
