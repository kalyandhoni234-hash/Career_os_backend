import logging
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.relationships.models import Contact, Interaction

logger = logging.getLogger(__name__)

relationships_bp = Blueprint("relationships", __name__)


def _contact_with_interactions(contact):
    data = contact.to_dict()
    data["interactions"] = [i.to_dict() for i in contact.interactions.order_by(Interaction.occurred_at.desc()).all()]
    return data


# ── List / Search Contacts ─────────────────────────────────


@relationships_bp.route("", methods=["GET"])
@login_required
def list_contacts():
    q = Contact.query.filter_by(user_id=current_user.id)

    opp_id = request.args.get("opportunity_id", type=int)
    if opp_id:
        q = q.filter_by(opportunity_id=opp_id)

    relationship = request.args.get("relationship")
    if relationship:
        q = q.filter_by(relationship=relationship)

    status = request.args.get("status")
    if status:
        q = q.filter_by(status=status)

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(
            db.or_(
                Contact.name.ilike(like),
                Contact.company.ilike(like),
                Contact.role.ilike(like),
                Contact.email.ilike(like),
            )
        )

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    total = q.count()
    contacts = q.order_by(Contact.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "contacts": [c.to_dict() for c in contacts],
        "total": total,
        "page": page,
        "per_page": per_page,
    }), 200


# ── Get Single Contact ─────────────────────────────────────


@relationships_bp.route("/<int:contact_id>", methods=["GET"])
@login_required
def get_contact(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"contact": _contact_with_interactions(contact)}), 200


# ── Create Contact ─────────────────────────────────────────


@relationships_bp.route("", methods=["POST"])
@login_required
def create_contact():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    next_follow_up = None
    if data.get("next_follow_up_at"):
        try:
            next_follow_up = datetime.fromisoformat(data["next_follow_up_at"])
        except (ValueError, TypeError):
            pass

    last_contacted = None
    if data.get("last_contacted_at"):
        try:
            last_contacted = datetime.fromisoformat(data["last_contacted_at"])
        except (ValueError, TypeError):
            pass

    contact = Contact(
        user_id=current_user.id,
        opportunity_id=data.get("opportunity_id"),
        name=name,
        role=data.get("role"),
        company=data.get("company"),
        email=data.get("email"),
        linkedin_url=data.get("linkedin_url"),
        phone=data.get("phone"),
        relationship=data.get("relationship", "other"),
        notes=data.get("notes"),
        status=data.get("status", "active"),
        last_contacted_at=last_contacted,
        next_follow_up_at=next_follow_up,
    )
    db.session.add(contact)
    db.session.commit()
    return jsonify({"contact": _contact_with_interactions(contact)}), 201


# ── Update Contact ─────────────────────────────────────────


@relationships_bp.route("/<int:contact_id>", methods=["PUT"])
@login_required
def update_contact(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("name", "role", "company", "email", "linkedin_url", "phone", "relationship", "notes", "status", "opportunity_id"):
        if field in data:
            setattr(contact, field, data[field])

    if "next_follow_up_at" in data:
        try:
            contact.next_follow_up_at = datetime.fromisoformat(data["next_follow_up_at"]) if data["next_follow_up_at"] else None
        except (ValueError, TypeError):
            pass

    if "last_contacted_at" in data:
        try:
            contact.last_contacted_at = datetime.fromisoformat(data["last_contacted_at"]) if data["last_contacted_at"] else None
        except (ValueError, TypeError):
            pass

    contact.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"contact": _contact_with_interactions(contact)}), 200


# ── Delete Contact ─────────────────────────────────────────


@relationships_bp.route("/<int:contact_id>", methods=["DELETE"])
@login_required
def delete_contact(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    db.session.delete(contact)
    db.session.commit()
    return jsonify({"message": "Contact deleted"}), 200


# ── Log Interaction ────────────────────────────────────────


@relationships_bp.route("/<int:contact_id>/interactions", methods=["POST"])
@login_required
def log_interaction(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first()
    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    data = request.get_json(silent=True) or {}
    occurred_at = datetime.now(timezone.utc)
    if data.get("occurred_at"):
        try:
            occurred_at = datetime.fromisoformat(data["occurred_at"])
        except (ValueError, TypeError):
            pass

    interaction = Interaction(
        contact_id=contact_id,
        interaction_type=data.get("interaction_type", "email"),
        notes=data.get("notes"),
        outcome=data.get("outcome"),
        occurred_at=occurred_at,
    )
    db.session.add(interaction)

    # Update last_contacted_at on the contact
    contact.last_contacted_at = occurred_at
    contact.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({"interaction": interaction.to_dict()}), 201


# ── Networking Health Score ────────────────────────────────


@relationships_bp.route("/health", methods=["GET"])
@login_required
def networking_health():
    uid = current_user.id
    total = Contact.query.filter_by(user_id=uid).count()

    if total == 0:
        return jsonify({
            "health": {
                "health_score": 0,
                "total_contacts": 0,
                "active_contacts": 0,
                "contacted_recently": 0,
                "with_upcoming_follow_up": 0,
                "relationship_diversity": 0,
                "breakdown": {},
            }
        }), 200

    active_contacts = Contact.query.filter_by(user_id=uid, status="active").count()

    # Contacted in last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    contacted_recently = Contact.query.filter(
        Contact.user_id == uid,
        Contact.last_contacted_at >= thirty_days_ago,
    ).count()

    # With upcoming follow-up
    with_upcoming = Contact.query.filter(
        Contact.user_id == uid,
        Contact.next_follow_up_at >= datetime.now(timezone.utc),
    ).count()

    # Diversity: count distinct relationship types
    rel_results = (
        db.session.query(Contact.relationship, db.func.count(Contact.id))
        .filter_by(user_id=uid)
        .group_by(Contact.relationship)
        .all()
    )
    breakdown = {r: c for r, c in rel_results}
    diversity = len(breakdown)

    # Score calculation
    coverage_score = min(100, total * 5)
    recency_score = round((contacted_recently / max(active_contacts, 1)) * 100)
    followup_score = min(100, with_upcoming * 20)
    diversity_score = min(100, diversity * 20)

    health_score = round(
        coverage_score * 0.3 + recency_score * 0.35 + followup_score * 0.2 + diversity_score * 0.15
    )

    return jsonify({
        "health": {
            "health_score": health_score,
            "total_contacts": total,
            "active_contacts": active_contacts,
            "contacted_recently": contacted_recently,
            "with_upcoming_follow_up": with_upcoming,
            "relationship_diversity": diversity,
            "breakdown": breakdown,
        }
    }), 200


# ── Due Follow-ups ─────────────────────────────────────────


@relationships_bp.route("/follow-ups", methods=["GET"])
@login_required
def due_follow_ups():
    now = datetime.now(timezone.utc)
    week_ahead = now + timedelta(days=7)

    contacts = Contact.query.filter(
        Contact.user_id == current_user.id,
        Contact.next_follow_up_at <= week_ahead,
        Contact.status == "active",
    ).order_by(Contact.next_follow_up_at.asc()).all()

    return jsonify({"follow_ups": [c.to_dict() for c in contacts]}), 200
