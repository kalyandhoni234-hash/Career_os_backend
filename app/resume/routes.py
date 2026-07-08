from flask import Blueprint

resume_bp = Blueprint("resume", __name__)

@resume_bp.route("/ping")
def ping():
    return {"blueprint": "resume", "status": "alive"}