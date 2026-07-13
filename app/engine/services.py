import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.extensions import db
from app.core.session import safe_commit
from app.auth.models import User
from app.opportunities.models import (
    SavedOpportunity,
    OpportunityMatchScore,
    InterviewPack,
)
from app.engine.models import RuleExecutionLog

logger = logging.getLogger(__name__)


def _log_execution(rule_name: str, user_id: Optional[int], summary: str, success: bool = True) -> None:
    log = RuleExecutionLog(
        rule_name=rule_name,
        user_id=user_id,
        summary=summary,
        success=success,
    )
    db.session.add(log)
    safe_commit()


def get_all_user_ids() -> list[int]:
    users = User.query.with_entities(User.id).all()
    return [u.id for u in users]


def check_follow_up_reminders() -> dict:
    """Flag saved applications in 'applied' stage where applied_at is 7+ days overdue."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    saved = SavedOpportunity.query.filter(
        SavedOpportunity.application_status == "applied",
        SavedOpportunity.applied_at.isnot(None),
        SavedOpportunity.applied_at <= cutoff,
    ).all()

    reminders = {}
    for s in saved:
        reminders.setdefault(s.user_id, []).append({
            "opportunity_id": s.opportunity_id,
            "applied_at": s.applied_at.isoformat(),
            "days_since": (now - s.applied_at).days,
        })

    for user_id, items in reminders.items():
        summary = f"Found {len(items)} application(s) needing follow-up"
        logger.info("User %d: %s", user_id, summary)
        _log_execution("follow_up_reminders", user_id, summary)

    return {
        "applications_flagged": sum(len(v) for v in reminders.values()),
        "users_affected": len(reminders),
    }


def check_networking_follow_ups() -> dict:
    """Check for contacts with past-due follow-ups via the relationships service."""
    from app.relationships.services import get_due_follow_ups

    user_ids = get_all_user_ids()
    total_due = 0
    users_with_due = 0

    for user_id in user_ids:
        due = get_due_follow_ups(user_id)
        if due:
            total_due += len(due)
            users_with_due += 1
            summary = f"Found {len(due)} contact(s) with due follow-up"
            _log_execution("networking_follow_ups", user_id, summary)

    return {"contacts_due": total_due, "users_affected": users_with_due}


def recompute_stale_scores() -> dict:
    """Recompute match and health scores for entries older than 7 days (or missing)."""
    from app.opportunities.services.match_engine import calculate_match_score
    from app.opportunities.services.health_score_service import compute_application_health
    from app.opportunities.services.skill_gap_service import analyze_opportunity_skill_gaps

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    saved_list = SavedOpportunity.query.all()
    recomputed = 0
    users_affected = set()

    for s in saved_list:
        score = OpportunityMatchScore.query.filter_by(
            user_id=s.user_id, opportunity_id=s.opportunity_id
        ).first()

        needs_recompute = not score or (score.created_at and score.created_at < cutoff)

        if needs_recompute:
            try:
                calculate_match_score(s.user_id, s.opportunity_id, force=True)
                compute_application_health(s.user_id, s.opportunity_id)
                analyze_opportunity_skill_gaps(s.user_id, s.opportunity_id, force=True)
                recomputed += 1
                users_affected.add(s.user_id)
            except Exception as e:
                logger.warning(
                    "Failed to recompute for user %d opp %d: %s",
                    s.user_id, s.opportunity_id, e,
                )

    for uid in users_affected:
        _log_execution("stale_score_recompute", uid, "Recomputed match scores, health, and skill gaps")

    return {"recomputed": recomputed, "users_affected": len(users_affected)}


def generate_interview_prep() -> dict:
    """Auto-generate interview prep for applications in 'interview' stage that lack an InterviewPack."""
    from app.opportunities.services.career_agent_service import generate_ai_career_advice

    interview_apps = SavedOpportunity.query.filter_by(
        application_status="interview"
    ).all()

    generated = 0
    users_affected = set()

    for s in interview_apps:
        existing = InterviewPack.query.filter_by(
            user_id=s.user_id, opportunity_id=s.opportunity_id
        ).first()
        if existing:
            continue

        try:
            generate_ai_career_advice(s.user_id, s.opportunity_id)
            generated += 1
            users_affected.add(s.user_id)
        except Exception as e:
            logger.warning(
                "Failed to generate interview prep for user %d opp %d: %s",
                s.user_id, s.opportunity_id, e,
            )

    for uid in users_affected:
        _log_execution("interview_prep", uid, "Generated interview preparation advice")

    return {"interview_packs_generated": generated, "users_affected": len(users_affected)}


def recompute_career_scores() -> dict:
    """Periodically recompute career scores for all users."""
    from app.career.services.career_score_service import compute_career_score

    user_ids = get_all_user_ids()
    recomputed = 0

    for user_id in user_ids:
        try:
            compute_career_score(user_id)
            recomputed += 1
        except Exception as e:
            logger.warning("Failed to recompute career score for user %d: %s", user_id, e)

    _log_execution("career_score_recompute", None, f"Recomputed scores for {recomputed} users")

    return {"users_recomputed": recomputed}


def generate_weekly_reports() -> dict:
    """Generate weekly career reports for all users."""
    from app.career.services.weekly_report_service import generate_weekly_report

    user_ids = get_all_user_ids()
    generated = 0

    for user_id in user_ids:
        try:
            report = generate_weekly_report(user_id)
            if report:
                generated += 1
        except Exception as e:
            logger.warning("Failed to generate weekly report for user %d: %s", user_id, e)

    _log_execution("weekly_report", None, f"Generated {generated} weekly reports")

    return {"reports_generated": generated}
