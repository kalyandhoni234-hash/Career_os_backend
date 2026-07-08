from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.resume.models import Resume

resume_bp = Blueprint("resume", __name__)

@resume_bp.route("/ping")
def ping():
    return {"blueprint": "resume", "status": "alive"}

@resume_bp.route("", methods=["GET"])
@login_required
def get_resume():
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        return jsonify({"resume": None}), 200

    return jsonify({
        "resume": {
            "id": resume.id,
            "full_name": resume.full_name,
            "email": resume.email,
            "phone": resume.phone,
            "location": resume.location,
            "summary": resume.summary,
            "experience": resume.experience,
            "education": resume.education,
            "projects": resume.projects,
            "skills": resume.skills,
        }
    }), 200

@resume_bp.route("", methods=["POST", "PUT"])
@login_required
def upsert_resume():
    data = request.get_json(silent=True) or {}

    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        resume = Resume(user_id=current_user.id)
        db.session.add(resume)

    resume.full_name = data.get("full_name", resume.full_name)
    resume.email = data.get("email", resume.email)
    resume.phone = data.get("phone", resume.phone)
    resume.location = data.get("location", resume.location)
    resume.summary = data.get("summary", resume.summary)
    resume.experience = data.get("experience", resume.experience)
    resume.education = data.get("education", resume.education)
    resume.projects = data.get("projects", resume.projects)
    resume.skills = data.get("skills", resume.skills)

    db.session.commit()

    return jsonify({"message": "Resume saved successfully", "id": resume.id}), 200
