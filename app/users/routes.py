from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.users.models import Profile

users_bp = Blueprint("users", __name__)

@users_bp.route("/ping")
def ping():
    return {"blueprint": "users", "status": "alive"}

@users_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"profile": None}), 200

    return jsonify({
        "profile": {
            "education": profile.education,
            "degree": profile.degree,
            "graduation_year": profile.graduation_year,
            "country": profile.country,
            "preferred_roles": profile.preferred_roles,
            "skills": profile.skills,
            "experience": profile.experience,
            "languages": profile.languages,
            "interests": profile.interests,
            "preferred_locations": profile.preferred_locations,
            "salary_expectation": profile.salary_expectation,
        }
    }), 200

@users_bp.route("/profile", methods=["POST", "PUT"])
@login_required
def upsert_profile():
    data = request.get_json(silent=True) or {}

    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)

    profile.education = data.get("education", profile.education)
    profile.degree = data.get("degree", profile.degree)
    profile.graduation_year = data.get("graduation_year", profile.graduation_year)
    profile.country = data.get("country", profile.country)
    profile.preferred_roles = data.get("preferred_roles", profile.preferred_roles)
    profile.skills = data.get("skills", profile.skills)
    profile.experience = data.get("experience", profile.experience)
    profile.languages = data.get("languages", profile.languages)
    profile.interests = data.get("interests", profile.interests)
    profile.preferred_locations = data.get("preferred_locations", profile.preferred_locations)
    profile.salary_expectation = data.get("salary_expectation", profile.salary_expectation)

    db.session.commit()

    return jsonify({"message": "Profile saved successfully"}), 200


@users_bp.route("/dashboard-summary", methods=["GET"])
@login_required
def dashboard_summary():
    from app.resume.models import Resume
    from app.jobs.models import Job
    from app.coach.models import CoachMessage
    from datetime import date

    resume = Resume.query.filter_by(user_id=current_user.id).first()
    jobs = Job.query.filter_by(user_id=current_user.id).all()

    active_statuses = ["applied", "oa", "interview"]
    active_applications = len([j for j in jobs if j.status in active_statuses])
    offers = len([j for j in jobs if j.status == "offer"])

    upcoming_deadlines = sorted(
        [
            {"company": j.company, "role": j.role, "deadline": j.deadline.isoformat()}
            for j in jobs
            if j.deadline and j.deadline >= date.today() and j.status in active_statuses
        ],
        key=lambda x: x["deadline"],
    )[:3]

    last_message = (
        CoachMessage.query.filter_by(user_id=current_user.id, role="assistant")
        .order_by(CoachMessage.created_at.desc())
        .first()
    )

    return jsonify({
        "has_resume": resume is not None,
        "resume_summary_set": bool(resume and resume.summary),
        "active_applications": active_applications,
        "offers": offers,
        "total_applications": len(jobs),
        "upcoming_deadlines": upcoming_deadlines,
        "last_coach_message": last_message.content if last_message else None,
        "last_coach_message_at": last_message.created_at.isoformat() if last_message else None,
    }), 200
