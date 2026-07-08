from flask import Blueprint

coach_bp = Blueprint("coach", __name__)

@coach_bp.route("/ping")
def ping():
    return {"blueprint": "coach", "status": "alive"}