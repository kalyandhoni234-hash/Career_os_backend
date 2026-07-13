import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.knowledge import services

logger = logging.getLogger(__name__)

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.route("/ping")
def ping():
    return {"blueprint": "knowledge", "status": "alive"}


@knowledge_bp.route("/interviews", methods=["GET"])
@login_required
def list_interviews():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 100)
    result = services.list_interviews(
        user_id=current_user.id,
        opportunity_id=request.args.get("opportunity_id", type=int),
        company=request.args.get("company"),
        page=page,
        per_page=per_page,
    )
    return jsonify(result), 200


@knowledge_bp.route("/interviews/<int:interview_id>", methods=["GET"])
@login_required
def get_interview(interview_id):
    result = services.get_interview(current_user.id, interview_id)
    if not result:
        return jsonify({"error": "Interview record not found"}), 404
    return jsonify({"interview": result}), 200


@knowledge_bp.route("/interviews", methods=["POST"])
@login_required
def create_interview():
    data = request.get_json(silent=True) or {}
    if not data.get("company") or not data.get("role"):
        return jsonify({"error": "company and role are required"}), 400
    result = services.create_interview(current_user.id, data)
    return jsonify({"interview": result}), 201


@knowledge_bp.route("/interviews/<int:interview_id>", methods=["PUT"])
@login_required
def update_interview(interview_id):
    data = request.get_json(silent=True) or {}
    result = services.update_interview(current_user.id, interview_id, data)
    if not result:
        return jsonify({"error": "Interview record not found"}), 404
    return jsonify({"interview": result}), 200


@knowledge_bp.route("/interviews/<int:interview_id>", methods=["DELETE"])
@login_required
def delete_interview(interview_id):
    if not services.delete_interview(current_user.id, interview_id):
        return jsonify({"error": "Interview record not found"}), 404
    return jsonify({"message": "Interview record deleted"}), 200


@knowledge_bp.route("/interviews/topics-by-company", methods=["GET"])
@login_required
def topics_by_company():
    result = services.get_topics_by_company(current_user.id)
    return jsonify({"topics_by_company": result}), 200


@knowledge_bp.route("/interviews/stats", methods=["GET"])
@login_required
def interview_stats():
    result = services.get_interview_stats(current_user.id)
    return jsonify({"stats": result}), 200
