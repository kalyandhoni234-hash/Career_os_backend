import logging
from app.extensions import db
from app.opportunities.models import Opportunity, OpportunitySkillGap

logger = logging.getLogger(__name__)


def analyze_opportunity_skill_gaps(user_id: int, opportunity_id: int, force: bool = False) -> dict:
    existing = OpportunitySkillGap.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    if existing and not force:
        return _gap_to_dict(existing)

    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return {"error": "Opportunity not found"}

    from app.resume.models import Resume

    resume = Resume.query.filter_by(user_id=user_id).first()

    user_skills = set()
    if resume and resume.skills:
        user_skills = {s.lower().strip() for s in resume.skills if isinstance(s, str)}

    from app.career.models import LearningProgress
    learning_skills = set()
    for lp in LearningProgress.query.filter_by(user_id=user_id).all():
        learning_skills.add(lp.skill_name.lower().strip())

    all_user_skills = user_skills | learning_skills

    required = set()
    if opp.tech_stack:
        required = {s.lower().strip() for s in opp.tech_stack if isinstance(s, str)}
    if opp.requirements:
        req_text = " ".join(opp.requirements)
        for skill in _TECH_KEYWORDS:
            if skill in req_text.lower():
                required.add(skill)

    current = list(user_skills & required)
    missing = list(required - all_user_skills)

    coverage = round((len(current) / len(required)) * 100) if required else 100

    ats_gain = {}
    for skill in missing:
        gain = _estimate_ats_gain_for_skill(skill)
        ats_gain[skill] = gain

    if len(missing) > 5:
        priority = "high"
    elif len(missing) > 2:
        priority = "medium"
    else:
        priority = "low"

    if existing:
        existing.missing_skills = missing
        existing.current_skills = current
        existing.required_skills = list(required)
        existing.ats_gain_estimates = ats_gain
        existing.coverage_pct = coverage
        existing.priority = priority
    else:
        existing = OpportunitySkillGap(
            user_id=user_id,
            opportunity_id=opportunity_id,
            missing_skills=missing,
            current_skills=current,
            required_skills=list(required),
            ats_gain_estimates=ats_gain,
            coverage_pct=coverage,
            priority=priority,
        )
        db.session.add(existing)
    db.session.commit()

    return _gap_to_dict(existing)


_TECH_KEYWORDS = {
    "python", "javascript", "typescript", "java", "go", "golang", "rust", "c++",
    "react", "angular", "vue", "node.js", "nodejs", "django", "flask", "fastapi",
    "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "terraform",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "kafka",
    "graphql", "rest", "grpc", "machine learning", "deep learning", "ai",
    "pytorch", "tensorflow", "pandas", "numpy", "spark", "hadoop",
    "ci/cd", "jenkins", "git", "linux", "bash", "sql",
}


def _estimate_ats_gain_for_skill(skill: str) -> int:
    premium = {
        "python": 8, "javascript": 7, "typescript": 7, "react": 8,
        "docker": 6, "kubernetes": 7, "aws": 8, "gcp": 6,
        "machine learning": 8, "sql": 6, "go": 7, "golang": 7,
        "system design": 8, "kafka": 5, "spark": 5, "terraform": 6,
        "redis": 4, "postgresql": 5, "mongodb": 4, "graphql": 5,
        "django": 6, "flask": 5, "fastapi": 5,
    }
    return premium.get(skill.lower(), 3)


def _gap_to_dict(gap: OpportunitySkillGap) -> dict:
    return {
        "id": gap.id,
        "opportunity_id": gap.opportunity_id,
        "missing_skills": gap.missing_skills or [],
        "current_skills": gap.current_skills or [],
        "required_skills": gap.required_skills or [],
        "ats_gain_estimates": gap.ats_gain_estimates or {},
        "coverage_pct": gap.coverage_pct,
        "priority": gap.priority,
    }
