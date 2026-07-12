"""Career Readiness Score Engine — unified scoring across all dimensions.

Each dimension is scored 0-100 based on evidence from the corresponding module.
Scores are cached in UnifiedProfile and snapshotted in ReadinessScoreSnapshot
for historical trend tracking.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.extensions import db

logger = logging.getLogger(__name__)


def compute_readiness_score(user_id: int) -> dict[str, Any]:
    """Compute the full career readiness score for a user across all dimensions.

    Returns the score breakdown and persists it to the database.
    """
    scores = _compute_all_dimensions(user_id)
    _persist_readiness(user_id, scores)
    _snapshot_score(user_id, scores)
    return scores


def _compute_all_dimensions(user_id: int) -> dict[str, Any]:
    """Compute scores for each dimension independently."""
    return {
        "overall": 0,
        "skills": _skill_score(user_id),
        "projects": _project_score(user_id),
        "resume": _resume_score(user_id),
        "experience": _experience_score(user_id),
        "interview": _interview_score(user_id),
        "applications": _application_score(user_id),
        "learning": _learning_score(user_id),
        "github": _github_score(user_id),
        "linkedin": _linkedin_score(user_id),
        "portfolio": _portfolio_score(user_id),
    }


def _skill_score(user_id: int) -> int:
    """Score based on number of skills, confidence levels, and category coverage."""
    from app.intelligence.models import SkillEvidence

    evidences = SkillEvidence.query.filter_by(user_id=user_id).all()
    if not evidences:
        return 0

    # Deduplicate by skill name
    skills: dict[str, float] = {}
    for e in evidences:
        key = e.skill_name
        if key not in skills or e.confidence > skills[key]:
            skills[key] = e.confidence

    if not skills:
        return 0

    total_skills = len(skills)
    avg_confidence = sum(skills.values()) / total_skills
    high_confidence = sum(1 for c in skills.values() if c >= 0.7)

    # Score: up to 40 for count (10+ skills = max), up to 40 for confidence, up to 20 for high-confidence ones
    count_score = min(40, total_skills * 4)
    confidence_score = int(avg_confidence * 40)
    mastery_score = min(20, high_confidence * 5)

    return min(100, count_score + confidence_score + mastery_score)


def _project_score(user_id: int) -> int:
    """Score based on projects, their complexity, and completeness."""
    from app.intelligence.models import CanonicalProject, ProjectIntelligence

    projects = CanonicalProject.query.filter_by(user_id=user_id).all()
    if not projects:
        return 0

    total = len(projects)
    has_intel = 0
    has_tests = 0
    has_readme = 0
    complexity_score = 0
    non_fork = sum(1 for p in projects if not p.is_fork)

    for p in projects:
        pi = ProjectIntelligence.query.filter_by(project_id=p.id).first()
        if pi:
            has_intel += 1
            if pi.has_tests:
                has_tests += 1
            if pi.has_readme:
                has_readme += 1
            complexity_map = {"beginner": 0, "intermediate": 1, "advanced": 2}
            complexity_score += complexity_map.get(pi.complexity, 0)
            if pi.resume_value >= 50:
                has_intel += 1  # bonus for high-value projects

    count_score = min(30, total * 6)
    quality_score = min(30, int((has_readme / max(total, 1)) * 15) + int((has_tests / max(total, 1)) * 15))
    complexity_avg = complexity_score / max(total, 1)
    complexity_bonus = min(20, int(complexity_avg * 10))
    non_fork_bonus = min(20, non_fork * 4)

    return min(100, count_score + quality_score + complexity_bonus + non_fork_bonus)


def _resume_score(user_id: int) -> int:
    """Score based on resume completeness, quality, and ATS readiness."""
    from app.resume.models import Resume

    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        return 0

    score = 0

    if resume.summary:
        score += 15
    if resume.experience and len(resume.experience) > 0:
        score += 20
    if resume.education and len(resume.education) > 0:
        score += 10
    if resume.skills and len(resume.skills) > 0:
        score += 15
    if resume.projects and len(resume.projects) > 0:
        score += 10
    if resume.certifications and len(resume.certifications) > 0:
        score += 10
    if resume.languages and len(resume.languages) > 0:
        score += 5
    if resume.custom_sections and len(resume.custom_sections) > 0:
        score += 5
    if resume.contact and isinstance(resume.contact, dict):
        contact = resume.contact
        if contact.get("email"):
            score += 3
        if contact.get("phone"):
            score += 2
        if contact.get("linkedin"):
            score += 2
        if contact.get("github"):
            score += 3

    return min(100, score)


def _experience_score(user_id: int) -> int:
    """Score based on work experience, positions, and duration."""
    from app.intelligence.models import CanonicalExperience

    experiences = CanonicalExperience.query.filter_by(user_id=user_id).all()
    if not experiences:
        return 0

    total = len(experiences)
    current = sum(1 for e in experiences if e.is_current)
    has_tech = sum(1 for e in experiences if e.technologies and len(e.technologies) > 0)

    count_score = min(40, total * 10)
    current_bonus = min(20, current * 10)
    tech_bonus = min(20, int((has_tech / max(total, 1)) * 20))
    description_score = min(20, sum(1 for e in experiences if e.description and len(e.description) > 50))

    return min(100, count_score + current_bonus + tech_bonus + description_score)


def _interview_score(user_id: int) -> int:
    """Score based on interview experience and preparation."""
    from app.jobs.models import Job

    interviews = Job.query.filter_by(user_id=user_id, status="interview").all()
    offers = Job.query.filter_by(user_id=user_id, status="offer").count()
    all_jobs = Job.query.filter_by(user_id=user_id).count()

    interview_count = len(interviews)
    count_score = min(40, interview_count * 15)
    offer_bonus = min(40, offers * 20)
    preparation = min(20, all_jobs * 2)

    return min(100, count_score + offer_bonus + preparation)


def _application_score(user_id: int) -> int:
    """Score based on application activity and pipeline health."""
    from app.jobs.models import Job

    jobs = Job.query.filter_by(user_id=user_id).all()
    if not jobs:
        return 0

    total = len(jobs)
    active = sum(1 for j in jobs if j.status in ("applied", "interview", "offer"))
    offers = sum(1 for j in jobs if j.status == "offer")
    rejected = sum(1 for j in jobs if j.status == "rejected")

    count_score = min(30, total * 3)
    active_score = min(30, active * 6)
    offer_score = min(25, offers * 25)
    resilience = max(0, 15 - rejected)  # deduct for rejections

    return min(100, count_score + active_score + offer_score + resilience)


def _learning_score(user_id: int) -> int:
    """Score based on roadmap progress, courses, and certifications."""
    from app.career.models import Roadmap, LessonProgress

    roadmaps = Roadmap.query.filter_by(user_id=user_id).all()
    lessons = LessonProgress.query.filter_by(user_id=user_id).all()
    from app.intelligence.models import CanonicalCertificate

    certs = CanonicalCertificate.query.filter_by(user_id=user_id).count()

    if not roadmaps and not lessons and not certs:
        return 0

    roadmap_progress = 0
    if roadmaps:
        roadmap_progress = int(sum(r.progress or 0 for r in roadmaps) / len(roadmaps))

    lesson_completed = sum(1 for lp in lessons if lp.status == "completed")
    lesson_score = min(30, lesson_completed * 2)
    roadmap_score = int(roadmap_progress * 0.4)
    cert_score = min(30, certs * 10)

    return min(100, roadmap_score + lesson_score + cert_score)


def _github_score(user_id: int) -> int:
    """Score based on GitHub integration quality."""
    from app.resume.models import Resume
    from app.integrations.models import Integration

    integration = Integration.query.filter_by(
        user_id=user_id, provider="github", connected=True
    ).first()
    if not integration:
        return 0

    resume = Resume.query.filter_by(user_id=user_id).first()
    projects = 0
    stars = 0

    if resume and resume.github_data:
        gh = resume.github_data
        if isinstance(gh, dict):
            projects = gh.get("public_repos", 0) or gh.get("repo_count", 0) or 0
            stars = gh.get("total_stars", 0) or 0

    from app.intelligence.models import CanonicalProject
    repo_count = CanonicalProject.query.filter_by(
        user_id=user_id, source="github"
    ).count()

    connected_score = 20
    repo_bonus = min(40, max(repo_count, projects) * 4)
    star_bonus = min(40, stars * 2)

    return min(100, connected_score + repo_bonus + star_bonus)


def _linkedin_score(user_id: int) -> int:
    """Score based on LinkedIn integration quality."""
    from app.integrations.models import Integration

    integration = Integration.query.filter_by(
        user_id=user_id, provider="linkedin", connected=True
    ).first()
    if not integration:
        return 0

    score = 20  # connected
    if integration.metadata_json:
        meta = integration.metadata_json
        if meta.get("headline"):
            score += 15
        if meta.get("connections_count") and meta["connections_count"] > 100:
            score += 20
        elif meta.get("connections_count") and meta["connections_count"] > 50:
            score += 10
        if meta.get("recommendations_count"):
            score += 10

    from app.intelligence.models import CanonicalExperience
    experiences = CanonicalExperience.query.filter_by(
        user_id=user_id, source="linkedin"
    ).count()
    score += min(35, experiences * 7)

    return min(100, score)


def _portfolio_score(user_id: int) -> int:
    """Score based on portfolio presence and quality."""
    from app.intelligence.models import CanonicalProject
    from app.resume.models import Resume

    projects = CanonicalProject.query.filter_by(user_id=user_id).all()
    resume = Resume.query.filter_by(user_id=user_id).first()

    score = 0

    pinned = sum(1 for p in projects if p.is_pinned)
    score += min(30, pinned * 10)

    public_repos = sum(1 for p in projects if p.url)
    score += min(30, public_repos * 3)

    if resume and resume.contact:
        contact = resume.contact
        if isinstance(contact, dict):
            if contact.get("portfolio_url") or contact.get("website"):
                score += 20
            if contact.get("github"):
                score += 10
            if contact.get("linkedin"):
                score += 10

    return min(100, score)


def _persist_readiness(user_id: int, scores: dict[str, Any]) -> None:
    """Cache the computed readiness scores in UnifiedProfile."""
    from app.intelligence.models import UnifiedProfile

    profile = UnifiedProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UnifiedProfile(user_id=user_id)
        db.session.add(profile)

    breakdown = {
        "skills": scores["skills"],
        "projects": scores["projects"],
        "resume": scores["resume"],
        "experience": scores["experience"],
        "interview": scores["interview"],
        "applications": scores["applications"],
        "learning": scores["learning"],
        "github": scores["github"],
        "linkedin": scores["linkedin"],
        "portfolio": scores["portfolio"],
    }

    overall = int(sum(breakdown.values()) / max(len(breakdown), 1))

    profile.career_readiness_score = overall
    profile.skill_readiness_score = scores["skills"]
    profile.project_readiness_score = scores["projects"]
    profile.resume_readiness_score = scores["resume"]
    profile.experience_readiness_score = scores["experience"]
    profile.interview_readiness_score = scores["interview"]
    profile.application_readiness_score = scores["applications"]
    profile.learning_readiness_score = scores["learning"]
    profile.github_readiness_score = scores["github"]
    profile.linkedin_readiness_score = scores["linkedin"]
    profile.portfolio_readiness_score = scores["portfolio"]

    # Update counts
    profile.skills_count = _count_skills(user_id)
    profile.projects_count = _count_projects(user_id)
    profile.applications_count = _count_applications(user_id)
    profile.interviews_count = _count_interviews(user_id)
    profile.certifications_count = _count_certs(user_id)
    profile.events_count = _count_events(user_id)

    profile.last_recalculated_at = datetime.now(timezone.utc)

    db.session.commit()


def _snapshot_score(user_id: int, scores: dict[str, Any]) -> None:
    """Create a historical snapshot for trend tracking."""
    from app.intelligence.models import ReadinessScoreSnapshot

    breakdown = {
        "skills": scores["skills"],
        "projects": scores["projects"],
        "resume": scores["resume"],
        "experience": scores["experience"],
        "interview": scores["interview"],
        "applications": scores["applications"],
        "learning": scores["learning"],
        "github": scores["github"],
        "linkedin": scores["linkedin"],
        "portfolio": scores["portfolio"],
    }

    overall = int(sum(breakdown.values()) / max(len(breakdown), 1))

    snapshot = ReadinessScoreSnapshot(
        user_id=user_id,
        overall_score=overall,
        skills_score=scores["skills"],
        projects_score=scores["projects"],
        resume_score=scores["resume"],
        experience_score=scores["experience"],
        interview_score=scores["interview"],
        applications_score=scores["applications"],
        learning_score=scores["learning"],
        github_score=scores["github"],
        linkedin_score=scores["linkedin"],
        portfolio_score=scores["portfolio"],
        breakdown=breakdown,
    )
    db.session.add(snapshot)
    db.session.commit()


def get_readiness_history(user_id: int, limit: int = 30) -> list[dict]:
    """Get historical readiness score snapshots."""
    from app.intelligence.models import ReadinessScoreSnapshot

    snapshots = (
        ReadinessScoreSnapshot.query.filter_by(user_id=user_id)
        .order_by(ReadinessScoreSnapshot.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "overall_score": s.overall_score,
            "breakdown": s.breakdown,
            "summary": s.summary,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in snapshots
    ]


def _count_skills(user_id: int) -> int:
    from app.intelligence.models import SkillEvidence
    return len(set(e.skill_name for e in SkillEvidence.query.filter_by(user_id=user_id).all()))


def _count_projects(user_id: int) -> int:
    from app.intelligence.models import CanonicalProject
    return CanonicalProject.query.filter_by(user_id=user_id).count()


def _count_applications(user_id: int) -> int:
    from app.jobs.models import Job
    return Job.query.filter_by(user_id=user_id).count()


def _count_interviews(user_id: int) -> int:
    from app.jobs.models import Job
    return Job.query.filter_by(user_id=user_id, status="interview").count()


def _count_certs(user_id: int) -> int:
    from app.intelligence.models import CanonicalCertificate
    return CanonicalCertificate.query.filter_by(user_id=user_id).count()


def _count_events(user_id: int) -> int:
    from app.intelligence.models import CareerEvent
    return CareerEvent.query.filter_by(user_id=user_id).count()
