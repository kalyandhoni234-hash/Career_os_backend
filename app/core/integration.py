"""Integration hooks — called after key mutations to keep all modules in sync.

Each function is invoked at the end of the relevant route handler so that
dependent data (career score, skill gaps, recommendations, analytics) is
recalculated immediately, keeping every module fresh without requiring an
external event bus.
"""

import logging
from datetime import datetime, timezone

from app.extensions import db
from app.core.session import safe_commit

logger = logging.getLogger(__name__)


def on_resume_changed(user_id: int) -> None:
    """Recalculate all dependent data when resume is created or updated.

    Triggers: skill-gap analysis, career-score recomputation,
              and AI recommendation regeneration.
    """
    try:
        from app.career.services.skill_graph_service import analyze_skill_gaps
        from app.career.services.career_score_service import compute_career_score
        from app.career.services.recommendation_service import generate_recommendations

        analyze_skill_gaps(user_id)
        compute_career_score(user_id)
        try:
            generate_recommendations(user_id, force=True)
        except Exception:
            db.session.rollback()
            logger.warning("Recommendation generation skipped (AI may be unavailable)", exc_info=True)

        logger.info("Integration: resume changed for user %s — skill gaps, score, and recommendations updated", user_id)
    except Exception as e:
        db.session.rollback()
        logger.error("Integration error on_resume_changed: %s", e, exc_info=True)


def on_roadmap_progress_changed(user_id: int, node_id: int) -> None:
    """Recalculate dependent data when roadmap node progress changes.

    Triggers: career-score recomputation (includes roadmap bonus).
    """
    try:
        from app.career.services.career_score_service import compute_career_score
        from app.career.services.recommendation_service import generate_recommendations

        compute_career_score(user_id)
        try:
            generate_recommendations(user_id)
        except Exception:
            db.session.rollback()
            logger.warning("Recommendation generation skipped", exc_info=True)

        logger.info("Integration: roadmap progress changed for user %s node %s — score updated", user_id, node_id)
    except Exception as e:
        db.session.rollback()
        logger.error("Integration error on_roadmap_progress_changed: %s", e, exc_info=True)


def on_application_changed(user_id: int, job_id: int) -> None:
    """Recalculate dependent data when job application is created or updated.

    Triggers: career-score recomputation and timeline event logging.
    """
    try:
        from app.career.services.career_score_service import compute_career_score
        from app.career.models import CareerTimelineEvent
        from app.jobs.models import Job

        compute_career_score(user_id)

        job = db.session.get(Job, job_id)
        if job and job.user_id == user_id:
            event = CareerTimelineEvent(
                user_id=user_id,
                event_type="application",
                title=f"Application {job.status}: {job.role} at {job.company}",
                event_date=datetime.now(timezone.utc),
                importance=3,
            )
            db.session.add(event)
            safe_commit()

        logger.info("Integration: application changed for user %s job %s — score updated", user_id, job_id)
    except Exception as e:
        db.session.rollback()
        logger.error("Integration error on_application_changed: %s", e, exc_info=True)


def on_profile_changed(user_id: int) -> None:
    """Recalculate dependent data when user profile is updated.

    Triggers: career-score recomputation, AI recommendation refresh,
              and personalized roadmap auto-generation.
    """
    try:
        from app.career.services.career_score_service import compute_career_score
        from app.career.services.recommendation_service import generate_recommendations

        compute_career_score(user_id)
        try:
            generate_recommendations(user_id)
        except Exception:
            logger.warning("Recommendation generation skipped", exc_info=True)

        # Auto-generate roadmap if user has a target role and no active roadmap
        from app.career.models import CareerProfile, Roadmap
        cp = CareerProfile.query.filter_by(user_id=user_id).first()
        if cp and cp.target_role:
            active_roadmap = Roadmap.query.filter_by(
                user_id=user_id, status="active"
            ).first()
            if not active_roadmap:
                try:
                    from app.career.services.roadmap_engine import generate_personalized_roadmap
                    generate_personalized_roadmap(user_id, target_role=cp.target_role)
                    logger.info("Auto-generated roadmap for user %s role=%s", user_id, cp.target_role)
                except Exception:
                    logger.warning("Roadmap auto-generation skipped", exc_info=True)

        logger.info("Integration: profile changed for user %s — score, recommendations, roadmap updated", user_id)
    except Exception as e:
        logger.error("Integration error on_profile_changed: %s", e, exc_info=True)
