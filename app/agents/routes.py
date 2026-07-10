import logging
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from app.agents.services import (
    get_agent_statuses,
    get_recent_tasks,
    run_agent,
    ensure_default_agents,
    get_agent_dashboard,
    get_agent_briefing,
)
from app.agents.models import AGENT_TYPES

logger = logging.getLogger(__name__)

agents_bp = Blueprint("agents", __name__)


@agents_bp.route("/ping")
def ping():
    return {"blueprint": "agents", "status": "alive"}


@agents_bp.route("", methods=["GET"])
@login_required
def list_agents():
    agents = get_agent_statuses(current_user.id)
    return jsonify({"agents": agents}), 200


@agents_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    ensure_default_agents(current_user.id)
    data = get_agent_dashboard(current_user.id)
    return jsonify(data), 200


@agents_bp.route("/tasks", methods=["GET"])
@login_required
def list_tasks():
    tasks = get_recent_tasks(current_user.id)
    return jsonify({"tasks": tasks}), 200


@agents_bp.route("/briefing", methods=["GET"])
@login_required
def briefing():
    data = get_agent_briefing(current_user.id)
    return jsonify(data), 200


@agents_bp.route("/job_discovery/results", methods=["GET"])
@login_required
def job_discovery_results():
    """Return opportunities discovered by the job discovery agent in the last 7 days."""
    from app.opportunities.models import Opportunity
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    opps = (
        Opportunity.query.filter(
            Opportunity.created_at >= cutoff,
            Opportunity.provider.in_(
                ["linkedin", "indeed", "naukri", "foundit", "internshala", "agent"]
            ),
        )
        .order_by(Opportunity.created_at.desc())
        .limit(20)
        .all()
    )

    return jsonify(
        {
            "discovered": [
                {
                    "id": o.id,
                    "title": o.title,
                    "company_name": o.company_name,
                    "company_logo": o.company_logo,
                    "location": o.location,
                    "remote_type": o.remote_type,
                    "salary_min": o.salary_min,
                    "salary_max": o.salary_max,
                    "currency": o.currency,
                    "employment_type": o.employment_type,
                    "tech_stack": o.tech_stack or [],
                    "posted_at": o.posted_at.isoformat() if o.posted_at else None,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "provider": o.provider,
                }
                for o in opps
            ],
            "total": len(opps),
        }
    ), 200


@agents_bp.route("/<agent_type>/run", methods=["POST"])
@login_required
def trigger_agent(agent_type):
    if agent_type not in AGENT_TYPES:
        return jsonify(
            {
                "error": f"Unknown agent type '{agent_type}'. Valid types: {', '.join(AGENT_TYPES)}"
            }
        ), 400
    result = run_agent(current_user.id, agent_type)
    if result is None:
        return jsonify({"error": "Agent not found"}), 404
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 409
    return jsonify(result), 200
