import logging
from datetime import date
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.intelligence.engine import (
    get_unified_profile,
    get_skills,
    get_experience,
    get_projects,
    get_education,
    get_certificates,
    get_interests,
    get_goals,
    get_events,
    sync_skills_from_source,
    sync_projects_from_source,
    sync_experience_from_source,
    log_event,
)
from app.intelligence.reasoning_engine import get_next_action

logger = logging.getLogger(__name__)

intelligence_bp = Blueprint("intelligence", __name__, url_prefix="/api/intelligence")

_next_action_cache: dict[int, tuple[str, dict]] = {}


@intelligence_bp.route("/next-action", methods=["GET"])
@login_required
def next_action():
    today = date.today().isoformat()
    cached_date, cached = _next_action_cache.get(current_user.id, (None, None))
    if cached_date == today and cached is not None:
        return jsonify({"action": cached, "cached": True}), 200

    try:
        action = get_next_action(current_user.id)
        _next_action_cache[current_user.id] = (today, action)
        return jsonify({"action": action, "cached": False}), 200
    except Exception as e:
        logger.error("Next-action failed for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({"error": "Failed to determine next action"}), 500


@intelligence_bp.route("/profile", methods=["GET"])
@login_required
def unified_profile():
    try:
        profile = get_unified_profile(current_user.id)
        return jsonify(profile), 200
    except Exception as e:
        logger.error("Failed to get unified profile: %s", e, exc_info=True)
        return jsonify({"error": "Failed to load profile", "reason": str(e)}), 500


@intelligence_bp.route("/profile/<section>", methods=["GET"])
@login_required
def profile_section(section):
    sections = {
        "skills": get_skills,
        "experience": get_experience,
        "projects": get_projects,
        "education": get_education,
        "certificates": get_certificates,
        "interests": get_interests,
        "goals": get_goals,
        "events": lambda uid: get_events(uid, limit=100),
    }
    fn = sections.get(section)
    if not fn:
        return jsonify({"error": f"Unknown section: {section}"}), 400
    try:
        return jsonify({section: fn(current_user.id)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@intelligence_bp.route("/completion", methods=["GET"])
@login_required
def profile_completion():
    profile = get_unified_profile(current_user.id)
    return jsonify({"completion": profile.get("completion", {})}), 200


@intelligence_bp.route("/events", methods=["GET"])
@login_required
def list_events():
    events = get_events(current_user.id)
    return jsonify({"events": events}), 200


@intelligence_bp.route("/events", methods=["POST"])
@login_required
def create_event():
    data = request.get_json(silent=True) or {}
    log_event(
        user_id=current_user.id,
        event_type=data.get("event_type", "manual"),
        title=data.get("title", "Untitled event"),
        description=data.get("description", ""),
        event_source=data.get("event_source", "manual"),
        source_id=data.get("source_id", ""),
    )
    return jsonify({"message": "Event created"}), 201


@intelligence_bp.route("/import", methods=["POST"])
@login_required
def import_data():
    data = request.get_json(silent=True) or {}
    source = data.get("source", "manual")
    section = data.get("section", "")
    items = data.get("items", [])

    if not items:
        return jsonify({"error": "No items to import"}), 400

    try:
        if section == "skills":
            ids = sync_skills_from_source(current_user.id, items, source)
            msg = f"Imported {len(ids)} skills from {source}"
        elif section == "projects":
            ids = sync_projects_from_source(current_user.id, items, source)
            msg = f"Imported {len(ids)} projects from {source}"
        elif section == "experience":
            ids = sync_experience_from_source(current_user.id, items, source)
            msg = f"Imported {len(ids)} experience entries from {source}"
        else:
            return jsonify({"error": f"Unknown section: {section}"}), 400

        log_event(current_user.id, "import", msg, event_source=source)
        db.session.commit()
        return jsonify({"message": msg, "ids": ids}), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Import failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500
