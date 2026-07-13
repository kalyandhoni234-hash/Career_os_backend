"""Career Intelligence Engine — the single source of truth for Career OS.

This is the central orchestrator. Every module reads from and writes to this engine.
It coordinates all sub-engines (skill graph, readiness score, project intelligence,
insights, achievements) and boots the event bus handlers at startup.
"""

import logging
from typing import Any

from app.extensions import db
from app.core.session import safe_commit
from app.intelligence.services.event_bus import Events, register, emit

logger = logging.getLogger(__name__)


# ── Core API ──────────────────────────────────────────────


def get_unified_profile(user_id: int) -> dict[str, Any] | None:
    """Get the complete unified profile for a user.

    This is the primary API for all frontend modules. It combines
    the cached UnifiedProfile with real-time computed data.
    """
    from app.intelligence.models import UnifiedProfile
    from app.career.models import CareerProfile
    from app.integrations.models import Integration

    profile = UnifiedProfile.query.filter_by(user_id=user_id).first()
    career = CareerProfile.query.filter_by(user_id=user_id).first()

    if not profile:
        profile = _init_unified_profile(user_id)

    github = Integration.query.filter(
        Integration.user_id == user_id,
        Integration.provider == "github",
        Integration.sync_status.in_(["connected", "syncing"]),
    ).first()
    linkedin = Integration.query.filter(
        Integration.user_id == user_id,
        Integration.provider == "linkedin",
        Integration.sync_status.in_(["connected", "syncing"]),
    ).first()

    return {
        "user_id": user_id,
        "dream_role": career.target_role if career else None,
        "experience_level": career.career_level if career else None,
        "career_stage": career.career_stage if career else None,
        "readiness": {
            "overall": profile.career_readiness_score or 0,
            "skills": profile.skill_readiness_score or 0,
            "projects": profile.project_readiness_score or 0,
            "resume": profile.resume_readiness_score or 0,
            "experience": profile.experience_readiness_score or 0,
            "interview": profile.interview_readiness_score or 0,
            "applications": profile.application_readiness_score or 0,
            "learning": profile.learning_readiness_score or 0,
            "github": profile.github_readiness_score or 0,
            "linkedin": profile.linkedin_readiness_score or 0,
            "portfolio": profile.portfolio_readiness_score or 0,
        },
        "counts": {
            "skills": profile.skills_count or 0,
            "projects": profile.projects_count or 0,
            "applications": profile.applications_count or 0,
            "interviews": profile.interviews_count or 0,
            "certifications": profile.certifications_count or 0,
            "achievements": profile.achievements_count or 0,
            "events": profile.events_count or 0,
        },
        "connections": {
            "github_connected": bool(github),
            "linkedin_connected": bool(linkedin),
            "resume_ready": profile.resume_ready or False,
            "resume_has_summary": profile.resume_has_summary or False,
            "onboarding_completed": profile.onboarding_completed or False,
        },
        "last_recalculated_at": profile.last_recalculated_at.isoformat()
        if profile.last_recalculated_at else None,
    }


def _init_unified_profile(user_id: int) -> Any:
    """Initialize a UnifiedProfile for a user if one doesn't exist."""
    from app.intelligence.models import UnifiedProfile
    profile = UnifiedProfile(user_id=user_id)
    db.session.add(profile)
    safe_commit()
    return profile


# ── Full intelligence refresh ────────────────────────────


def refresh_all(user_id: int) -> dict[str, Any]:
    """Refresh ALL computed data for a user.

    Called after any significant event to ensure everything is up to date.
    Uses the event bus to trigger individual recalculations.
    """
    from app.intelligence.services.readiness_score_engine import compute_readiness_score
    from app.intelligence.services.insight_engine import generate_insights
    from app.intelligence.services.achievement_engine import check_achievements

    # 1. Recompute readiness score (also updates UnifiedProfile counts)
    scores = compute_readiness_score(user_id)

    # 2. Generate fresh insights
    insights = generate_insights(user_id)

    # 3. Check for new achievements
    new_achievements = check_achievements(user_id)

    # 4. Update counts in UnifiedProfile
    _update_counts(user_id)

    # 5. Emit score recalculated event
    emit(Events.SCORE_RECALCULATED, user_id, {"scores": scores})

    return {
        "scores": scores,
        "insights": insights[:5],
        "new_achievements": new_achievements,
    }


def _update_counts(user_id: int) -> None:
    """Update cached counts in UnifiedProfile."""
    from app.intelligence.models import (
        UnifiedProfile, SkillEvidence, CanonicalProject,
        CareerAchievement, CareerEvent, CanonicalCertificate,
    )
    from app.jobs.models import Job
    from app.career.models import Roadmap, LessonProgress

    profile = UnifiedProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return

    profile.skills_count = len(set(
        e.skill_name for e in SkillEvidence.query.filter_by(user_id=user_id).all()
    ))
    profile.projects_count = CanonicalProject.query.filter_by(user_id=user_id).count()
    profile.applications_count = Job.query.filter_by(user_id=user_id).count()
    profile.interviews_count = Job.query.filter_by(user_id=user_id, status="interview").count()
    profile.interviews_completed = Job.query.filter_by(user_id=user_id, status="offer").count()
    profile.certifications_count = CanonicalCertificate.query.filter_by(user_id=user_id).count()
    profile.achievements_count = CareerAchievement.query.filter_by(user_id=user_id).count()
    profile.roadmaps_count = Roadmap.query.filter_by(user_id=user_id).count()
    profile.events_count = CareerEvent.query.filter_by(user_id=user_id).count()

    # Roadmap progress
    lessons = LessonProgress.query.filter_by(user_id=user_id).all()
    if lessons:
        completed = sum(1 for lp in lessons if lp.status == "completed")
        profile.roadmap_progress_pct = int((completed / len(lessons)) * 100) if lessons else 0

    # Connection status
    from app.integrations.models import Integration
    from app.resume.models import Resume

    profile.github_connected = Integration.query.filter(
        Integration.user_id == user_id,
        Integration.provider == "github",
        Integration.sync_status.in_(["connected", "syncing"]),
    ).count() > 0
    profile.linkedin_connected = Integration.query.filter(
        Integration.user_id == user_id,
        Integration.provider == "linkedin",
        Integration.sync_status.in_(["connected", "syncing"]),
    ).count() > 0

    resume = Resume.query.filter_by(user_id=user_id).first()
    profile.resume_ready = resume is not None
    profile.resume_has_summary = bool(resume and resume.summary)

    safe_commit()


# ── Event handlers ────────────────────────────────────────


def _on_profile_changed(user_id: int, event_data: dict | None = None) -> None:
    """Handle profile changes — refresh readiness and insights."""
    refresh_all(user_id)
    _update_counts(user_id)


def _on_skill_added(user_id: int, event_data: dict | None = None) -> None:
    """Handle skill additions — update skill graph and refresh."""
    refresh_all(user_id)


def _on_project_created(user_id: int, event_data: dict | None = None) -> None:
    """Handle project creation — analyze project and update everything."""
    from app.intelligence.services.project_intelligence import analyze_project

    data = (event_data or {}).get("data", {})
    project_id = data.get("project_id")
    if project_id:
        analyze_project(project_id)
    refresh_all(user_id)


def _on_resume_updated(user_id: int, event_data: dict | None = None) -> None:
    """Handle resume updates — refresh scores and insights."""
    refresh_all(user_id)


def _on_integration_synced(user_id: int, event_data: dict | None = None) -> None:
    """Handle GitHub/LinkedIn sync — detect skills and refresh."""

    data = (event_data or {}).get("data", {})
    provider = data.get("provider", "")

    if provider == "github":
        _import_github_skills(user_id)

    refresh_all(user_id)


def _on_roadmap_lesson_completed(user_id: int, event_data: dict | None = None) -> None:
    """Handle lesson completion — add skill evidence and refresh."""
    from app.intelligence.services.skill_graph_engine import add_skill_evidence

    data = (event_data or {}).get("data", {})
    skills = data.get("skills_gained", [])
    lesson_id = data.get("lesson_id")

    for skill in skills:
        add_skill_evidence(
            user_id=user_id,
            skill_name=skill,
            source="roadmap",
            source_id=lesson_id,
            roadmap_lesson_id=lesson_id,
            confidence=0.7,
        )

    refresh_all(user_id)


def _on_application_event(user_id: int, event_data: dict | None = None) -> None:
    """Handle application events — refresh scores."""
    refresh_all(user_id)


def _on_achievement_unlocked(user_id: int, event_data: dict | None = None) -> None:
    """Handle new achievements — update counts, potentially trigger notifications."""
    from app.intelligence.models import UnifiedProfile

    profile = UnifiedProfile.query.filter_by(user_id=user_id).first()
    if profile:
        from app.intelligence.models import CareerAchievement
        profile.achievements_count = CareerAchievement.query.filter_by(user_id=user_id).count()
        safe_commit()


# ── GitHub skill import ──────────────────────────────────


def _import_github_skills(user_id: int) -> None:
    """Import skills from GitHub repositories."""
    from app.intelligence.services.skill_graph_engine import add_skill_evidence
    from app.intelligence.models import CanonicalProject

    projects = CanonicalProject.query.filter_by(user_id=user_id, source="github").all()
    for project in projects:
        from app.intelligence.services.project_intelligence import analyze_project
        pi_data = analyze_project(project.id)
        if pi_data:
            for skill in pi_data.get("inferred_skills", []):
                add_skill_evidence(
                    user_id=user_id,
                    skill_name=skill,
                    source="github",
                    source_id=str(project.id),
                    project_id=project.id,
                    confidence=0.5,
                )


# ── Bootstrap: register all event handlers ───────────────


def bootstrap_engine() -> None:
    """Register all event handlers. Called once at app startup."""
    register(Events.PROFILE_UPDATED, _on_profile_changed)
    register(Events.DREAM_ROLE_CHANGED, _on_profile_changed)
    register(Events.SKILL_ADDED, _on_skill_added)
    register(Events.RESUME_UPLOADED, _on_resume_updated)
    register(Events.RESUME_UPDATED, _on_resume_updated)
    register(Events.PROJECT_CREATED, _on_project_created)
    register(Events.PROJECT_UPDATED, _on_project_created)
    register(Events.GITHUB_SYNCED, _on_integration_synced)
    register(Events.LINKEDIN_IMPORTED, _on_integration_synced)
    register(Events.ROADMAP_LESSON_COMPLETED, _on_roadmap_lesson_completed)
    register(Events.ROADMAP_COMPLETED, _on_roadmap_lesson_completed)
    register(Events.APPLICATION_SUBMITTED, _on_application_event)
    register(Events.APPLICATION_STATUS_CHANGED, _on_application_event)
    register(Events.APPLICATION_OFFER, _on_application_event)
    register(Events.INTERVIEW_SCHEDULED, _on_application_event)
    register(Events.INTERVIEW_COMPLETED, _on_application_event)
    register(Events.ACHIEVEMENT_UNLOCKED, _on_achievement_unlocked)
    register(Events.SCORE_RECALCULATED, _on_achievement_unlocked)
    register(Events.GOAL_CREATED, _on_profile_changed)
    register(Events.GOAL_COMPLETED, _on_profile_changed)

    logger.info("Career Intelligence Engine bootstrapped with %d event handlers",
                len(register.__self__) if hasattr(register, "__self__") else "all")
