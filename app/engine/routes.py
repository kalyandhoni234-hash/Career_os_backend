from flask import Blueprint, jsonify
from flask_login import login_required

from app.engine.models import RuleExecutionLog
from app.engine.scheduler import scheduler

engine_bp = Blueprint("engine", __name__)


@engine_bp.route("/api/engine/status")
@login_required
def engine_status():
    """Return the scheduler status and list of registered jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return jsonify({
        "running": scheduler.running,
        "jobs": jobs,
    })


@engine_bp.route("/api/engine/logs")
@login_required
def engine_logs():
    """Return the most recent rule execution logs."""
    logs = (
        RuleExecutionLog.query
        .order_by(RuleExecutionLog.executed_at.desc())
        .limit(50)
        .all()
    )

    return jsonify({
        "logs": [
            {
                "id": log.id,
                "rule_name": log.rule_name,
                "user_id": log.user_id,
                "summary": log.summary,
                "success": log.success,
                "executed_at": log.executed_at.isoformat() if log.executed_at else None,
            }
            for log in logs
        ]
    })
