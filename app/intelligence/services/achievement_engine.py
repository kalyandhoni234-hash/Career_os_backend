"""Achievement Engine — auto-awards achievements based on user milestones.

Achievements are defined declaratively with a checker function that evaluates
whether the user has met the criteria. The engine checks all unearned
achievements for a user after relevant events.
"""

import logging
from datetime import datetime, timezone
from typing import Callable

from app.extensions import db
from app.core.session import safe_commit

logger = logging.getLogger(__name__)

# ── Achievement Definitions ───────────────────────────────

AchievementCheck = Callable[[int], bool]


class AchievementDef:
    def __init__(
        self,
        code: str,
        title: str,
        description: str,
        icon: str,
        category: str,
        rarity: str = "common",
        check: AchievementCheck | None = None,
    ):
        self.code = code
        self.title = title
        self.description = description
        self.icon = icon
        self.category = category
        self.rarity = rarity
        self.check = check


_ACHIEVEMENT_REGISTRY: dict[str, AchievementDef] = {}


def define(code: str, title: str, description: str, icon: str,
           category: str, rarity: str = "common"):
    """Decorator to register an achievement definition."""
    def decorator(check_func: AchievementCheck):
        _ACHIEVEMENT_REGISTRY[code] = AchievementDef(
            code=code, title=title, description=description,
            icon=icon, category=category, rarity=rarity, check=check_func,
        )
        return check_func
    return decorator


# ── Achievement Checks ────────────────────────────────────


@define("first_project", "First Project", "Created your first project", "folder", "projects")
def _check_first_project(user_id: int) -> bool:
    from app.intelligence.models import CanonicalProject
    return CanonicalProject.query.filter_by(user_id=user_id).count() >= 1


@define("three_projects", "Project Trio", "Completed three projects", "layers", "projects")
def _check_three_projects(user_id: int) -> bool:
    from app.intelligence.models import CanonicalProject
    return CanonicalProject.query.filter_by(user_id=user_id).count() >= 3


@define("ten_skills", "Skill Collector", "Added 10 skills to your profile", "brain", "skills", "uncommon")
def _check_ten_skills(user_id: int) -> bool:
    from app.intelligence.models import SkillEvidence
    skills = set(e.skill_name for e in SkillEvidence.query.filter_by(user_id=user_id).all())
    return len(skills) >= 10


@define("twenty_skills", "Polyglot", "Added 20 skills to your profile", "stars", "skills", "rare")
def _check_twenty_skills(user_id: int) -> bool:
    from app.intelligence.models import SkillEvidence
    skills = set(e.skill_name for e in SkillEvidence.query.filter_by(user_id=user_id).all())
    return len(skills) >= 20


@define("master_skill", "Master of One", "Reached 90%+ confidence in any skill", "trophy", "skills", "rare")
def _check_master_skill(user_id: int) -> bool:
    from app.intelligence.models import SkillEvidence
    evidences = SkillEvidence.query.filter_by(user_id=user_id).all()
    skills: dict[str, float] = {}
    for e in evidences:
        key = e.skill_name
        if key not in skills or e.confidence > skills[key]:
            skills[key] = e.confidence
    return any(c >= 0.9 for c in skills.values())


@define("github_connected", "GitHub Connected", "Connected your GitHub account", "github", "integrations")
def _check_github_connected(user_id: int) -> bool:
    from app.integrations.models import Integration
    return Integration.query.filter_by(
        user_id=user_id, provider="github", connected=True
    ).count() > 0


@define("linkedin_connected", "Networker", "Connected your LinkedIn account", "linkedin", "integrations")
def _check_linkedin_connected(user_id: int) -> bool:
    from app.integrations.models import Integration
    return Integration.query.filter_by(
        user_id=user_id, provider="linkedin", connected=True
    ).count() > 0


@define("first_resume", "Resume Ready", "Created your first resume", "file-text", "resume")
def _check_first_resume(user_id: int) -> bool:
    from app.resume.models import Resume
    return Resume.query.filter_by(user_id=user_id).count() > 0


@define("resume_ats_80", "ATS Ace", "Achieved 80+ ATS score on resume", "shield-check", "resume", "uncommon")
def _check_resume_ats_80(user_id: int) -> bool:
    from app.resume.models import Resume
    resume = Resume.query.filter_by(user_id=user_id).first()
    if resume and resume.ats_score:
        return resume.ats_score >= 80
    return False


@define("five_applications", "Active Applicant", "Applied to 5 jobs", "send", "applications")
def _check_five_applications(user_id: int) -> bool:
    from app.jobs.models import Job
    return Job.query.filter_by(user_id=user_id).count() >= 5


@define("twenty_applications", "Persistent", "Applied to 20 jobs", "rocket", "applications", "uncommon")
def _check_twenty_applications(user_id: int) -> bool:
    from app.jobs.models import Job
    return Job.query.filter_by(user_id=user_id).count() >= 20


@define("first_interview", "Interview Ready", "Got your first interview", "calendar-check", "interviews")
def _check_first_interview(user_id: int) -> bool:
    from app.jobs.models import Job
    return Job.query.filter_by(user_id=user_id, status="interview").count() >= 1


@define("first_offer", "Offer Accepted", "Received your first job offer", "award", "interviews", "rare")
def _check_first_offer(user_id: int) -> bool:
    from app.jobs.models import Job
    return Job.query.filter_by(user_id=user_id, status="offer").count() >= 1


@define("roadmap_started", "Learning Journey", "Started a learning roadmap", "book-open", "learning")
def _check_roadmap_started(user_id: int) -> bool:
    from app.career.models import Roadmap
    return Roadmap.query.filter_by(user_id=user_id).count() >= 1


@define("roadmap_completed", "Roadmap Master", "Completed an entire roadmap", "graduation-cap", "learning", "rare")
def _check_roadmap_completed(user_id: int) -> bool:
    from app.career.models import Roadmap
    return Roadmap.query.filter_by(user_id=user_id, status="completed").count() >= 1


@define("fifty_lessons", "Dedicated Learner", "Completed 50 roadmap lessons", "zap", "learning", "uncommon")
def _check_fifty_lessons(user_id: int) -> bool:
    from app.career.models import LessonProgress
    return LessonProgress.query.filter_by(user_id=user_id, status="completed").count() >= 50


@define("score_80", "Career Ready", "Reached 80+ Career Readiness Score", "target", "milestone", "epic")
def _check_score_80(user_id: int) -> bool:
    from app.intelligence.models import UnifiedProfile
    profile = UnifiedProfile.query.filter_by(user_id=user_id).first()
    return profile is not None and (profile.career_readiness_score or 0) >= 80


@define("certification_added", "Certified", "Added your first certification", "certificate", "learning")
def _check_certification_added(user_id: int) -> bool:
    from app.intelligence.models import CanonicalCertificate
    return CanonicalCertificate.query.filter_by(user_id=user_id).count() >= 1


@define("event_milestone", "On a Roll", "Generated 50 career events", "activity", "milestone", "uncommon")
def _check_event_milestone(user_id: int) -> bool:
    from app.intelligence.models import CareerEvent
    return CareerEvent.query.filter_by(user_id=user_id).count() >= 50


@define("onboarding_complete", "Welcome to Career OS", "Completed your onboarding", "smile", "milestone")
def _check_onboarding_complete(user_id: int) -> bool:
    return True  # checked via event, not via DB query


# ── Engine ────────────────────────────────────────────────


def check_achievements(user_id: int) -> list[dict]:
    """Check all unearned achievements for a user and award any that qualify."""
    from app.intelligence.models import CareerAchievement

    earned = set(
        a.code for a in CareerAchievement.query.filter_by(user_id=user_id).all()
    )

    newly_unlocked = []
    for code, ach in _ACHIEVEMENT_REGISTRY.items():
        if code in earned:
            continue
        if ach.check and ach.check(user_id):
            now = datetime.now(timezone.utc)
            record = CareerAchievement(
                user_id=user_id,
                code=code,
                title=ach.title,
                description=ach.description,
                icon=ach.icon,
                category=ach.category,
                rarity=ach.rarity,
                unlocked_at=now,
            )
            db.session.add(record)
            newly_unlocked.append({
                "code": code,
                "title": ach.title,
                "description": ach.description,
                "icon": ach.icon,
                "category": ach.category,
                "rarity": ach.rarity,
                "unlocked_at": now.isoformat(),
            })

    if newly_unlocked:
        safe_commit()

    return newly_unlocked


def check_achievements_on_event(user_id: int, event_data: dict | None = None) -> None:
    """Called after relevant events to check for new achievements."""
    newly = check_achievements(user_id)
    for ach in newly:
        from app.intelligence.services.event_bus import Events, emit
        emit(Events.ACHIEVEMENT_UNLOCKED, user_id, {"achievement": ach})


def get_achievements(user_id: int) -> list[dict]:
    """Get all achievements for a user."""
    from app.intelligence.models import CareerAchievement

    records = (
        CareerAchievement.query.filter_by(user_id=user_id)
        .order_by(CareerAchievement.unlocked_at.desc())
        .all()
    )

    total = len(records)
    by_rarity = {"common": 0, "uncommon": 0, "rare": 0, "epic": 0, "legendary": 0}
    for r in records:
        by_rarity[r.rarity] = by_rarity.get(r.rarity, 0) + 1

    return {
        "achievements": [
            {
                "code": r.code,
                "title": r.title,
                "description": r.description,
                "icon": r.icon,
                "category": r.category,
                "rarity": r.rarity,
                "unlocked_at": r.unlocked_at.isoformat() if r.unlocked_at else None,
            }
            for r in records
        ],
        "total": total,
        "by_rarity": by_rarity,
        "available": len(_ACHIEVEMENT_REGISTRY),
    }


def get_achievement_codes() -> list[str]:
    """Get all registered achievement codes."""
    return list(_ACHIEVEMENT_REGISTRY.keys())
