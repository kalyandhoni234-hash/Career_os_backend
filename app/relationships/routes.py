import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.relationships import services

logger = logging.getLogger(__name__)

relationships_bp = Blueprint("relationships", __name__)


@relationships_bp.route("/ping")
def ping():
    return {"blueprint": "relationships", "status": "alive"}


@relationships_bp.route("", methods=["GET"])
@login_required
def list_contacts_endpoint():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 100)
    result = services.list_contacts(
        user_id=current_user.id,
        opportunity_id=request.args.get("opportunity_id", type=int),
        relationship=request.args.get("relationship"),
        status=request.args.get("status"),
        page=page,
        per_page=per_page,
    )
    return jsonify(result), 200


@relationships_bp.route("/<int:contact_id>", methods=["GET"])
@login_required
def get_contact_endpoint(contact_id):
    result = services.get_contact(current_user.id, contact_id)
    if not result:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"contact": result}), 200


@relationships_bp.route("", methods=["POST"])
@login_required
def create_contact_endpoint():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    result = services.create_contact(current_user.id, data)
    return jsonify({"contact": result}), 201


@relationships_bp.route("/<int:contact_id>", methods=["PUT"])
@login_required
def update_contact_endpoint(contact_id):
    data = request.get_json(silent=True) or {}
    result = services.update_contact(current_user.id, contact_id, data)
    if not result:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"contact": result}), 200


@relationships_bp.route("/<int:contact_id>", methods=["DELETE"])
@login_required
def delete_contact_endpoint(contact_id):
    if not services.delete_contact(current_user.id, contact_id):
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"message": "Contact deleted"}), 200


@relationships_bp.route("/<int:contact_id>/interactions", methods=["POST"])
@login_required
def log_interaction_endpoint(contact_id):
    data = request.get_json(silent=True) or {}
    if not data.get("interaction_type"):
        return jsonify({"error": "interaction_type is required"}), 400
    result = services.log_interaction(current_user.id, contact_id, data)
    if not result:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"interaction": result}), 201


@relationships_bp.route("/health", methods=["GET"])
@login_required
def networking_health():
    result = services.get_networking_health(current_user.id)
    return jsonify({"health": result}), 200


@relationships_bp.route("/follow-ups", methods=["GET"])
@login_required
def due_follow_ups():
    result = services.get_due_follow_ups(current_user.id)
    return jsonify({"follow_ups": result}), 200
