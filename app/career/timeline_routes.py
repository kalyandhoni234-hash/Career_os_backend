import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.core.session import safe_commit
from app.career.models import CareerTimelineEvent

logger = logging.getLogger(__name__)

timeline_bp = Blueprint("timeline", __name__)


def _event_to_dict(e):
    return {
        "id": e.id,
        "title": e.title,
        "description": e.description or "",
        "event_type": e.event_type,
        "category": e.event_type,
        "event_date": e.event_date.isoformat() if e.event_date else None,
        "importance": e.importance,
        "status": e.status or "completed",
        "tags": e.tags or [],
        "related_goal_id": e.related_goal_id,
        "attachment_url": e.attachment_url,
        "visibility": e.visibility or "public",
        "is_favorite": e.is_favorite or False,
        "is_pinned": e.is_pinned or False,
        "sort_order": e.sort_order or 0,
        "metadata": e.metadata_json or {},
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


# ── List / Search / Filter Events ─────────────────────────


@timeline_bp.route("/api/timeline/events", methods=["GET"])
@login_required
def list_events():
    uid = current_user.id
    query = CareerTimelineEvent.query.filter_by(user_id=uid)

    category = request.args.get("category")
    if category:
        query = query.filter(CareerTimelineEvent.event_type == category)

    status = request.args.get("status")
    if status:
        query = query.filter(CareerTimelineEvent.status == status)

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                CareerTimelineEvent.title.ilike(like),
                CareerTimelineEvent.description.ilike(like),
            )
        )

    favorite = request.args.get("favorite")
    if favorite == "true":
        query = query.filter(CareerTimelineEvent.is_favorite)

    pinned = request.args.get("pinned")
    if pinned == "true":
        query = query.filter(CareerTimelineEvent.is_pinned)

    sort = request.args.get("sort", "newest")
    if sort == "oldest":
        query = query.order_by(CareerTimelineEvent.event_date.asc())
    else:
        query = query.order_by(
            CareerTimelineEvent.is_pinned.desc(), CareerTimelineEvent.event_date.desc()
        )

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    total = query.count()
    events = query.offset(offset).limit(limit).all()

    return jsonify(
        {
            "events": [_event_to_dict(e) for e in events],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }
    ), 200


# ── Grouped Timeline (by year → month) ─────────────────────


@timeline_bp.route("/api/timeline/grouped", methods=["GET"])
@login_required
def grouped_timeline():
    uid = current_user.id
    query = CareerTimelineEvent.query.filter_by(user_id=uid)

    category = request.args.get("category")
    if category:
        query = query.filter(CareerTimelineEvent.event_type == category)

    status_filter = request.args.get("status")
    if status_filter:
        query = query.filter(CareerTimelineEvent.status == status_filter)

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                CareerTimelineEvent.title.ilike(like),
                CareerTimelineEvent.description.ilike(like),
            )
        )

    events = query.order_by(CareerTimelineEvent.event_date.desc()).all()
    years = {}
    for e in events:
        if not e.event_date:
            continue
        year = str(e.event_date.year)
        month = e.event_date.strftime("%B")
        if year not in years:
            years[year] = {}
        if month not in years[year]:
            years[year][month] = []
        years[year][month].append(_event_to_dict(e))

    return jsonify(
        {
            "years": years,
            "year_list": sorted(years.keys(), reverse=True),
            "total": len(events),
        }
    ), 200


# ── Get Single Event ───────────────────────────────────────


@timeline_bp.route("/api/timeline/events/<int:event_id>", methods=["GET"])
@login_required
def get_event(event_id):
    event = CareerTimelineEvent.query.filter_by(
        id=event_id, user_id=current_user.id
    ).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify({"event": _event_to_dict(event)}), 200


# ── Create Event ───────────────────────────────────────────


@timeline_bp.route("/api/timeline/events", methods=["POST"])
@login_required
def create_event():
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    try:
        event_date_str = data.get("event_date")
        if event_date_str:
            event_date = datetime.fromisoformat(event_date_str)
        else:
            event_date = datetime.now(timezone.utc)
    except (ValueError, TypeError):
        event_date = datetime.now(timezone.utc)

    max_order = (
        db.session.query(db.func.max(CareerTimelineEvent.sort_order))
        .filter_by(user_id=current_user.id)
        .scalar()
        or 0
    )

    event = CareerTimelineEvent(
        user_id=current_user.id,
        event_type=data.get("event_type", "custom"),
        title=title,
        description=data.get("description", ""),
        event_date=event_date,
        importance=data.get("importance", 1),
        status=data.get("status", "completed"),
        tags=data.get("tags", []),
        related_goal_id=data.get("related_goal_id"),
        attachment_url=data.get("attachment_url"),
        visibility=data.get("visibility", "public"),
        is_favorite=data.get("is_favorite", False),
        is_pinned=data.get("is_pinned", False),
        sort_order=max_order + 1,
        metadata_json=data.get("metadata", {}),
    )
    try:
        db.session.add(event)
        safe_commit()
        return jsonify({"event": _event_to_dict(event)}), 201
    except Exception as e:
        db.session.rollback()
        logger.error("Failed to create timeline event: %s", str(e), exc_info=True)
        return jsonify({"error": "Failed to create timeline event"}), 500


# ── Update Event ───────────────────────────────────────────


@timeline_bp.route("/api/timeline/events/<int:event_id>", methods=["PUT"])
@login_required
def update_event(event_id):
    event = CareerTimelineEvent.query.filter_by(
        id=event_id, user_id=current_user.id
    ).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in [
        "title",
        "description",
        "event_type",
        "status",
        "visibility",
        "attachment_url",
    ]:
        if field in data:
            setattr(event, field, data[field])
    for field in ["importance", "sort_order"]:
        if field in data:
            setattr(event, field, int(data[field]))
    for field in ["is_favorite", "is_pinned"]:
        if field in data:
            setattr(event, field, bool(data[field]))
    if "tags" in data and isinstance(data["tags"], list):
        event.tags = data["tags"]
    if "event_date" in data:
        try:
            event.event_date = datetime.fromisoformat(data["event_date"])
        except (ValueError, TypeError):
            pass
    if "metadata" in data and isinstance(data["metadata"], dict):
        event.metadata_json = data["metadata"]
    if "related_goal_id" in data:
        event.related_goal_id = data["related_goal_id"]
    safe_commit()
    return jsonify({"event": _event_to_dict(event)}), 200


# ── Delete Event ───────────────────────────────────────────


@timeline_bp.route("/api/timeline/events/<int:event_id>", methods=["DELETE"])
@login_required
def delete_event(event_id):
    event = CareerTimelineEvent.query.filter_by(
        id=event_id, user_id=current_user.id
    ).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404
    db.session.delete(event)
    safe_commit()
    return jsonify({"message": "Event deleted"}), 200


# ── Duplicate Event ────────────────────────────────────────


@timeline_bp.route("/api/timeline/events/<int:event_id>/duplicate", methods=["POST"])
@login_required
def duplicate_event(event_id):
    original = CareerTimelineEvent.query.filter_by(
        id=event_id, user_id=current_user.id
    ).first()
    if not original:
        return jsonify({"error": "Event not found"}), 404
    max_order = (
        db.session.query(db.func.max(CareerTimelineEvent.sort_order))
        .filter_by(user_id=current_user.id)
        .scalar()
        or 0
    )
    event = CareerTimelineEvent(
        user_id=current_user.id,
        event_type=original.event_type,
        title=f"{original.title} (copy)",
        description=original.description,
        event_date=datetime.now(timezone.utc),
        importance=original.importance,
        status="planned",
        tags=original.tags or [],
        related_goal_id=original.related_goal_id,
        attachment_url=original.attachment_url,
        visibility=original.visibility,
        sort_order=max_order + 1,
        metadata_json=original.metadata_json or {},
    )
    db.session.add(event)
    safe_commit()
    return jsonify({"event": _event_to_dict(event)}), 201


# ── Toggle Pin / Favorite ──────────────────────────────────


@timeline_bp.route("/api/timeline/events/<int:event_id>/pin", methods=["POST"])
@login_required
def toggle_pin(event_id):
    event = CareerTimelineEvent.query.filter_by(
        id=event_id, user_id=current_user.id
    ).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404
    event.is_pinned = not event.is_pinned
    safe_commit()
    return jsonify({"is_pinned": event.is_pinned}), 200


@timeline_bp.route("/api/timeline/events/<int:event_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(event_id):
    event = CareerTimelineEvent.query.filter_by(
        id=event_id, user_id=current_user.id
    ).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404
    event.is_favorite = not event.is_favorite
    safe_commit()
    return jsonify({"is_favorite": event.is_favorite}), 200


@timeline_bp.route("/api/timeline/events/reorder", methods=["PUT"])
@login_required
def reorder_events():
    data = request.get_json(silent=True) or {}
    order_map = data.get("order", {})
    for event_id, order in order_map.items():
        event = CareerTimelineEvent.query.filter_by(
            id=int(event_id), user_id=current_user.id
        ).first()
        if event:
            event.sort_order = order
    safe_commit()
    return jsonify({"message": "Reordered"}), 200


# ── Event Categories (for filter UI) ──────────────────────


@timeline_bp.route("/api/timeline/categories", methods=["GET"])
@login_required
def list_categories():
    uid = current_user.id
    results = (
        db.session.query(
            CareerTimelineEvent.event_type, db.func.count(CareerTimelineEvent.id)
        )
        .filter_by(user_id=uid)
        .group_by(CareerTimelineEvent.event_type)
        .order_by(db.func.count(CareerTimelineEvent.id).desc())
        .all()
    )
    categories = []
    all_count = CareerTimelineEvent.query.filter_by(user_id=uid).count()
    for event_type, count in results:
        categories.append({"type": event_type, "count": count})
    return jsonify({"categories": categories, "total": all_count}), 200


# ── Stats ──────────────────────────────────────────────────


@timeline_bp.route("/api/timeline/stats", methods=["GET"])
@login_required
def timeline_stats():
    uid = current_user.id
    total = CareerTimelineEvent.query.filter_by(user_id=uid).count()
    pinned = CareerTimelineEvent.query.filter_by(user_id=uid, is_pinned=True).count()
    favorites = CareerTimelineEvent.query.filter_by(
        user_id=uid, is_favorite=True
    ).count()
    planned = CareerTimelineEvent.query.filter_by(user_id=uid, status="planned").count()
    in_progress = CareerTimelineEvent.query.filter_by(
        user_id=uid, status="in_progress"
    ).count()
    completed = CareerTimelineEvent.query.filter_by(
        user_id=uid, status="completed"
    ).count()

    return jsonify(
        {
            "total": total,
            "pinned": pinned,
            "favorites": favorites,
            "planned": planned,
            "in_progress": in_progress,
            "completed": completed,
        }
    ), 200
