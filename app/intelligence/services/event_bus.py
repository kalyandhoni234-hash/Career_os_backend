"""Central event bus for Career OS.

Every action across the platform emits events that propagate through registered
handlers, keeping all modules in sync without direct coupling.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from flask import has_app_context
from app.core.session import safe_commit

logger = logging.getLogger(__name__)


# ── Event type constants ──────────────────────────────────

class Events:
    # Profile
    PROFILE_UPDATED = "profile.updated"
    DREAM_ROLE_CHANGED = "dream_role.changed"
    SKILL_ADDED = "skill.added"
    SKILL_REMOVED = "skill.removed"
    EXPERIENCE_ADDED = "experience.added"

    # Resume
    RESUME_UPLOADED = "resume.uploaded"
    RESUME_UPDATED = "resume.updated"
    RESUME_EXPORTED = "resume.exported"

    # Projects
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"

    # GitHub / LinkedIn
    GITHUB_SYNCED = "github.synced"
    LINKEDIN_IMPORTED = "linkedin.imported"

    # Roadmap
    ROADMAP_GENERATED = "roadmap.generated"
    ROADMAP_LESSON_COMPLETED = "roadmap.lesson_completed"
    ROADMAP_MODULE_COMPLETED = "roadmap.module_completed"
    ROADMAP_PHASE_COMPLETED = "roadmap.phase_completed"
    ROADMAP_COMPLETED = "roadmap.completed"
    ROADMAP_PROGRESS_UPDATED = "roadmap.progress_updated"

    # Applications
    APPLICATION_SUBMITTED = "application.submitted"
    APPLICATION_STATUS_CHANGED = "application.status_changed"
    APPLICATION_REJECTED = "application.rejected"
    APPLICATION_OFFER = "application.offer"

    # Interviews
    INTERVIEW_SCHEDULED = "interview.scheduled"
    INTERVIEW_COMPLETED = "interview.completed"

    # Certifications
    CERTIFICATION_ADDED = "certification.added"

    # Learning
    COURSE_FINISHED = "course.finished"
    LEARNING_RESOURCE_COMPLETED = "learning.resource_completed"

    # Goals
    GOAL_CREATED = "goal.created"
    GOAL_COMPLETED = "goal.completed"

    # Career Score
    SCORE_RECALCULATED = "score.recalculated"

    # Achievements
    ACHIEVEMENT_UNLOCKED = "achievement.unlocked"


# ── Event Bus ─────────────────────────────────────────────

_handler_registry: dict[str, list[Callable]] = {}


def register(event_type: str, handler: Callable) -> None:
    """Register a handler function for an event type."""
    _handler_registry.setdefault(event_type, []).append(handler)


def emit(event_type: str, user_id: int, data: dict[str, Any] | None = None) -> None:
    """Emit an event to all registered handlers.

    Handlers are called synchronously. Expensive handlers should defer work
    to background jobs (e.g. via a task queue in the future).
    """
    if not has_app_context():
        logger.warning("No app context — skipping event %s for user %s", event_type, user_id)
        return

    from app.extensions import db

    handlers = _handler_registry.get(event_type, [])
    if not handlers:
        logger.debug("No handlers registered for event: %s", event_type)
        return

    payload = {
        "event_type": event_type,
        "user_id": user_id,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    for handler in handlers:
        try:
            handler(user_id=user_id, event_data=payload)
        except Exception:
            logger.error(
                "Handler %s failed for event %s user %s",
                handler.__name__, event_type, user_id, exc_info=True,
            )

    # Persist to career_events table
    try:
        from app.intelligence.models import CareerEvent
        evt = CareerEvent(
            user_id=user_id,
            event_type=event_type,
            title=_event_title(event_type, data),
            description=payload.get("data", {}).get("description", ""),
            event_source="system",
            occurred_at=datetime.now(timezone.utc),
            metadata_json=payload,
        )
        db.session.add(evt)
        safe_commit()
    except Exception:
        db.session.rollback()
        logger.warning("Failed to persist event %s for user %s", event_type, user_id, exc_info=True)


def _event_title(event_type: str, data: dict | None) -> str:
    """Generate a human-readable title from an event type."""
    titles = {
        Events.PROFILE_UPDATED: "Profile Updated",
        Events.DREAM_ROLE_CHANGED: "Dream Role Changed",
        Events.SKILL_ADDED: "Skill Added",
        Events.RESUME_UPLOADED: "Resume Uploaded",
        Events.RESUME_UPDATED: "Resume Updated",
        Events.RESUME_EXPORTED: "Resume Exported",
        Events.PROJECT_CREATED: "Project Created",
        Events.PROJECT_UPDATED: "Project Updated",
        Events.GITHUB_SYNCED: "GitHub Synced",
        Events.LINKEDIN_IMPORTED: "LinkedIn Imported",
        Events.ROADMAP_GENERATED: "Roadmap Generated",
        Events.ROADMAP_LESSON_COMPLETED: "Lesson Completed",
        Events.ROADMAP_COMPLETED: "Roadmap Completed",
        Events.APPLICATION_SUBMITTED: "Application Submitted",
        Events.APPLICATION_OFFER: "Offer Received!",
        Events.INTERVIEW_SCHEDULED: "Interview Scheduled",
        Events.INTERVIEW_COMPLETED: "Interview Completed",
        Events.CERTIFICATION_ADDED: "Certification Added",
        Events.COURSE_FINISHED: "Course Finished",
        Events.GOAL_CREATED: "Goal Created",
        Events.GOAL_COMPLETED: "Goal Completed",
        Events.ACHIEVEMENT_UNLOCKED: "Achievement Unlocked!",
    }
    return titles.get(event_type, event_type.replace(".", " ").title())


# ── Decorator for convenient handler registration ─────────

def on(event_type: str):
    """Decorator to register a function as an event handler."""
    def decorator(func: Callable):
        register(event_type, func)
        return func
    return decorator
