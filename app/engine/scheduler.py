import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(daemon=True)


def init_scheduler(app) -> None:
    """Register all background rule jobs and start the scheduler.

    Each job is wrapped with a Flask app context so database access works.
    """

    def job_wrapper(func):
        def wrapper(*args, **kwargs):
            with app.app_context():
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error("Rule engine job '%s' failed: %s", func.__name__, e, exc_info=True)

        wrapper.__name__ = func.__name__
        return wrapper

    from app.engine.services import (
        check_follow_up_reminders,
        check_networking_follow_ups,
        recompute_stale_scores,
        generate_interview_prep,
        generate_weekly_reports,
        recompute_career_scores,
    )

    scheduler.add_job(
        job_wrapper(check_follow_up_reminders),
        IntervalTrigger(hours=6),
        id="follow_up_reminders",
        replace_existing=True,
        name="Check follow-up reminders for applied jobs",
    )

    scheduler.add_job(
        job_wrapper(check_networking_follow_ups),
        IntervalTrigger(hours=6),
        id="networking_follow_ups",
        replace_existing=True,
        name="Check past-due networking follow-ups",
    )

    scheduler.add_job(
        job_wrapper(recompute_stale_scores),
        IntervalTrigger(days=1),
        id="stale_score_recompute",
        replace_existing=True,
        name="Recompute stale match and health scores",
    )

    scheduler.add_job(
        job_wrapper(recompute_career_scores),
        IntervalTrigger(days=1),
        id="career_score_recompute",
        replace_existing=True,
        name="Recompute career scores for all users",
    )

    scheduler.add_job(
        job_wrapper(generate_interview_prep),
        IntervalTrigger(hours=12),
        id="interview_prep",
        replace_existing=True,
        name="Generate interview prep for interview-stage applications",
    )

    scheduler.add_job(
        job_wrapper(generate_weekly_reports),
        CronTrigger(day_of_week="sun", hour=0, minute=0),
        id="weekly_reports",
        replace_existing=True,
        name="Generate weekly career reports",
    )

    if scheduler.running:
        logger.debug("Scheduler already running — skipping duplicate start")
        return

    scheduler.start()
    logger.info(
        "Background rule engine started with 6 registered jobs — "
        "follow-ups (6h), networking (6h), stale scores (24h), "
        "career scores (24h), interview prep (12h), weekly reports (Sun 00:00)"
    )
