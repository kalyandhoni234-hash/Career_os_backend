from datetime import datetime, timedelta, date
from app.extensions import db
from app.career.models import CareerReport, AIRecommendation, LearningProgress, CareerScoreSnapshot
from app.career.services.career_score_service import compute_career_score
from app.career.services.career_memory_service import build_career_memory


def generate_weekly_report(user_id):
    """Generate or retrieve the latest weekly career report."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Check if report already exists for this week
    existing = CareerReport.query.filter_by(
        user_id=user_id, week_start=week_start, week_end=week_end
    ).first()
    if existing:
        return _serialize_report(existing)

    # Get scores
    old_snapshots = CareerScoreSnapshot.query.filter_by(
        user_id=user_id
    ).order_by(
        CareerScoreSnapshot.created_at.desc()
    ).limit(2).all()
    score_before = old_snapshots[-1].overall_score if len(old_snapshots) >= 2 else 0
    current_score = compute_career_score(user_id)
    score_after = current_score["overall_score"]

    memory = build_career_memory(user_id)

    # Generate achievements from the week
    achievements = _get_weekly_achievements(user_id, week_start)

    # Get recommendations
    active_recs = AIRecommendation.query.filter_by(
        user_id=user_id, is_dismissed=False, is_completed=False
    ).order_by(AIRecommendation.priority.desc()).limit(3).all()

    metrics = {
        "resume_score": current_score["breakdown"]["resume_score"],
        "ats_score": current_score["breakdown"]["ats_score"],
        "applications_score": current_score["breakdown"]["applications_score"],
        "applications_total": memory.get("applications", {}).get("total_applications", 0),
        "interview_count": memory.get("applications", {}).get("interview_count", 0),
        "offer_count": memory.get("applications", {}).get("offer_count", 0),
        "skills_learning": len(memory.get("learning", [])),
        "roadmap_progress": max((r.get("progress", 0) or 0) for r in memory.get("roadmaps", [])) if memory.get("roadmaps") else 0,
    }

    report = CareerReport(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        score_before=score_before,
        score_after=score_after,
        metrics=metrics,
        achievements=achievements,
        recommendations=[
            {"title": r.title, "impact": r.impact_score, "category": r.category}
            for r in active_recs
        ],
        summary=_generate_summary(score_before, score_after, metrics, achievements),
    )
    db.session.add(report)
    db.session.commit()

    return _serialize_report(report)


def _get_weekly_achievements(user_id, since_date):
    """Get achievements from the past week."""
    from app.career.models import CareerTimelineEvent

    achievements = []

    # New skills learned
    recent_learning = LearningProgress.query.filter(
        LearningProgress.user_id == user_id,
        LearningProgress.updated_at >= datetime.combine(since_date, datetime.min.time()),
    ).all()
    for lp in recent_learning:
        if lp.proficiency >= 60:
            achievements.append(f"Progressed in {lp.skill_name} ({lp.proficiency}%)")

    # Timeline events
    recent_events = CareerTimelineEvent.query.filter(
        CareerTimelineEvent.user_id == user_id,
        CareerTimelineEvent.event_date >= datetime.combine(since_date, datetime.min.time()),
    ).order_by(CareerTimelineEvent.event_date.desc()).all()
    for e in recent_events:
        achievements.append(e.title)

    return achievements[:10]


def _generate_summary(score_before, score_after, metrics, achievements):
    """Generate a plain-text summary of the week."""
    parts = []
    delta = score_after - score_before
    if delta > 0:
        parts.append(f"Your Career Score increased by {delta} points ({score_before} → {score_after}).")
    elif delta == 0:
        parts.append(f"Your Career Score held steady at {score_after}.")
    else:
        parts.append(f"Your Career Score changed by {delta} points ({score_before} → {score_after}).")

    if metrics.get("skills_learning", 0) > 0:
        parts.append(f"You're learning {metrics['skills_learning']} skills.")
    if metrics.get("applications_total", 0) > 0:
        parts.append(f"You have {metrics['applications_total']} total applications.")
    if metrics.get("interview_count", 0) > 0:
        parts.append(f"Interviews: {metrics['interview_count']}.")
    if achievements:
        parts.append(f"Highlights: {'; '.join(achievements[:3])}.")

    return " ".join(parts)


def get_previous_reports(user_id):
    """Get all previous weekly reports for a user."""
    reports = CareerReport.query.filter_by(user_id=user_id)\
        .order_by(CareerReport.created_at.desc()).limit(20).all()
    return [_serialize_report(r) for r in reports]


def _serialize_report(report):
    """Serialize a CareerReport model to dict."""
    return {
        "id": report.id,
        "week_start": report.week_start.isoformat() if report.week_start else None,
        "week_end": report.week_end.isoformat() if report.week_end else None,
        "score_before": report.score_before,
        "score_after": report.score_after,
        "score_change": report.score_after - report.score_before,
        "metrics": report.metrics,
        "achievements": report.achievements or [],
        "recommendations": report.recommendations or [],
        "summary": report.summary or "",
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
