"""Notification Engine — generates intelligent notifications based on events.

Notifications are created automatically by event handlers and provide
actionable information to the user.
"""

import logging
from datetime import datetime, timezone

from app.extensions import db
from app.core.session import safe_commit

logger = logging.getLogger(__name__)


def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str | None = None,
    action_link: str | None = None,
    action_label: str | None = None,
    priority: int = 0,
    metadata_json: dict | None = None,
) -> dict:
    """Create a notification for a user."""
    from app.intelligence.models import Notification

    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        action_link=action_link,
        action_label=action_label,
        priority=priority,
        metadata_json=metadata_json or {},
    )
    db.session.add(notification)
    safe_commit()

    return {
        "id": notification.id,
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "action_link": action_link,
        "action_label": action_label,
        "priority": priority,
        "is_read": False,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def get_notifications(
    user_id: int,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """Get notifications for a user."""
    from app.intelligence.models import Notification

    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    query = query.order_by(Notification.created_at.desc()).limit(limit)

    return [
        {
            "id": n.id,
            "notification_type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "action_link": n.action_link,
            "action_label": n.action_label,
            "priority": n.priority,
            "is_read": n.is_read,
            "is_dismissed": n.is_dismissed,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in query.all()
    ]


def mark_read(notification_id: int, user_id: int) -> bool:
    """Mark a notification as read."""
    from app.intelligence.models import Notification

    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if not notification:
        return False
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    safe_commit()
    return True


def mark_all_read(user_id: int) -> int:
    """Mark all notifications as read. Returns count marked."""
    from app.intelligence.models import Notification

    count = Notification.query.filter_by(user_id=user_id, is_read=False).update(
        {"is_read": True, "read_at": datetime.now(timezone.utc)}
    )
    safe_commit()
    return count


def get_unread_count(user_id: int) -> int:
    """Get count of unread notifications."""
    from app.intelligence.models import Notification
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


# ── Event-based notification creators ─────────────────────


def notify_achievement_unlocked(user_id: int, achievement: dict) -> None:
    """Create a notification for a newly unlocked achievement."""
    create_notification(
        user_id=user_id,
        notification_type="achievement",
        title=f"Achievement Unlocked: {achievement['title']}",
        message=achievement.get("description", ""),
        priority=7,
        metadata_json={"achievement_code": achievement.get("code")},
    )


def notify_score_change(user_id: int, old_score: int, new_score: int) -> None:
    """Notify user of a readiness score change."""
    direction = "improved" if new_score > old_score else "changed"
    create_notification(
        user_id=user_id,
        notification_type="score_change",
        title=f"Career Readiness Score {direction}",
        message=f"Your score went from {old_score} to {new_score}.",
        priority=5 if new_score > old_score else 3,
        action_link="/dashboard",
    )


def notify_interview_reminder(user_id: int, company: str, role: str, date: str) -> None:
    """Remind user about an upcoming interview."""
    create_notification(
        user_id=user_id,
        notification_type="interview_reminder",
        title=f"Interview Tomorrow: {role} at {company}",
        message=f"Your interview for {role} at {company} is scheduled for {date}. "
                f"Check the Interview Hub for preparation resources.",
        priority=10,
        action_link="/coach",
        action_label="Prepare Now",
    )


def notify_roadmap_suggestion(user_id: int, title: str, message: str, roadmap_id: int) -> None:
    """Suggest the user continue their roadmap."""
    create_notification(
        user_id=user_id,
        notification_type="roadmap",
        title=title,
        message=message,
        priority=6,
        action_link=f"/roadmaps?id={roadmap_id}",
        action_label="Continue Learning",
    )


def notify_resume_suggestion(user_id: int, title: str, message: str) -> None:
    """Suggest resume improvements."""
    create_notification(
        user_id=user_id,
        notification_type="resume",
        title=title,
        message=message,
        priority=5,
        action_link="/resume",
        action_label="Edit Resume",
    )
