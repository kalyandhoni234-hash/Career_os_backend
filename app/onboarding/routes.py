import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.users.models import Profile
from app.career.models import (
    UserEducation,
    UserSkill,
    UserInterest,
    CareerProfile,
    CareerGoal,
    UserPreference,
)
from app.resume.models import Resume

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint("onboarding", __name__)


def _get_or_create_profile(user_id):
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.session.add(profile)
        db.session.flush()
    return profile


def _get_or_create_career_profile(user_id):
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    if not cp:
        cp = CareerProfile(user_id=user_id)
        db.session.add(cp)
        db.session.flush()
    return cp


def _get_or_create_preferences(user_id):
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = UserPreference(user_id=user_id)
        db.session.add(pref)
        db.session.flush()
    return pref


def _get_or_create_resume(user_id):
    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        resume = Resume(user_id=user_id)
        db.session.add(resume)
        db.session.flush()
    return resume


STEP_LABELS = {
    0: "Welcome",
    1: "Basic Info",
    2: "Education",
    3: "Career",
    4: "Skills",
    5: "Interests",
    6: "Goals",
    7: "Connect",
    8: "AI Preferences",
}

TOTAL_STEPS = 8


@onboarding_bp.route("/api/onboarding/status", methods=["GET"])
@login_required
def get_status():
    return jsonify({
        "onboarding_completed": current_user.onboarding_completed or False,
        "onboarding_step": current_user.onboarding_step or 0,
        "total_steps": TOTAL_STEPS,
        "step_label": STEP_LABELS.get(current_user.onboarding_step or 0, "Welcome"),
    }), 200


@onboarding_bp.route("/api/onboarding/step/<int:step>", methods=["GET"])
@login_required
def get_step(step):
    uid = current_user.id
    data = {}
    try:
        if step == 1:
            profile = Profile.query.filter_by(user_id=uid).first()
            resume = Resume.query.filter_by(user_id=uid).first()
            data = {
                "full_name": resume.full_name if resume else "",
                "preferred_name": "",
                "date_of_birth": profile.date_of_birth if profile else "",
                "country": profile.country if profile else "",
                "state": profile.state if profile else "",
                "city": profile.city if profile else "",
                "timezone": profile.timezone if profile else "",
                "profile_picture": profile.profile_picture if profile else "",
            }
        elif step == 2:
            edu = UserEducation.query.filter_by(user_id=uid).order_by(UserEducation.order).first()
            if edu:
                data = {
                    "status": "student",
                    "college": edu.institution,
                    "degree": edu.degree,
                    "branch": edu.branch or "",
                    "grad_year": edu.graduation_year,
                    "semester": edu.current_semester,
                    "cgpa": edu.cgpa,
                }
            career_profile = CareerProfile.query.filter_by(user_id=uid).first()
            if career_profile and career_profile.career_level:
                data["status"] = career_profile.career_level
        elif step == 3:
            cp = CareerProfile.query.filter_by(user_id=uid).first()
            if cp:
                data = {
                    "current_role": cp.position or "",
                    "dream_role": cp.target_role or "",
                    "experience": cp.years_experience or 0,
                    "industry": cp.preferred_industry or "",
                    "employment_status": cp.employment_type or "",
                    "salary": cp.target_salary or "",
                    "country": cp.preferred_country or "",
                    "work_preference": cp.work_preference or "remote",
                }
        elif step == 4:
            skills = UserSkill.query.filter_by(user_id=uid).order_by(UserSkill.name).all()
            data = {"skills": [{"name": s.name} for s in skills]}
        elif step == 5:
            interests = UserInterest.query.filter_by(user_id=uid).all()
            data = {"interests": [{"name": i.name} for i in interests]}
        elif step == 6:
            goals = CareerGoal.query.filter_by(user_id=uid).all()
            data = {
                "goals": [
                    {
                        "title": g.title,
                        "target_role": g.target_role or "",
                        "target_company": g.target_company or "",
                        "status": g.status,
                        "priority": g.priority,
                        "category": g.category or "career",
                    }
                    for g in goals
                ]
            }
        elif step == 7:
            from app.integrations.models import Integration
            integrations = Integration.query.filter_by(user_id=uid).all()
            data = {
                "connected": {i.provider: True for i in integrations},
                "providers": [i.provider for i in integrations],
            }
        elif step == 8:
            pref = UserPreference.query.filter_by(user_id=uid).first()
            if pref:
                data = {
                    "ai_tone": pref.ai_tone or "professional",
                    "reminder_freq": pref.reminder_freq or "weekly",
                    "weekly_reports": pref.weekly_reports if pref.weekly_reports is not None else True,
                    "roadmap_gen": pref.roadmap_gen if pref.roadmap_gen is not None else True,
                    "daily_motivation": pref.daily_motivation if pref.daily_motivation is not None else True,
                }

        return jsonify({"step": step, "data": data}), 200

    except Exception as e:
        logger.error("Failed to load step %s: %s", step, str(e), exc_info=True)
        return jsonify({"error": f"Failed to load step {step}", "reason": str(e)}), 500


@onboarding_bp.route("/api/onboarding/step/<int:step>", methods=["POST"])
@login_required
def save_step(step):
    uid = current_user.id
    body = request.get_json(silent=True) or {}
    data = body.get("data", body)

    try:
        if step == 1:
            profile = _get_or_create_profile(uid)
            resume = _get_or_create_resume(uid)
            full_name = data.get("full_name", "")
            if full_name:
                resume.full_name = full_name
                parts = full_name.strip().split(None, 1)
                profile.first_name = parts[0] if parts else ""
                profile.last_name = parts[1] if len(parts) > 1 else ""
            profile.date_of_birth = data.get("date_of_birth", profile.date_of_birth or "")
            profile.country = data.get("country", profile.country or "")
            profile.state = data.get("state", profile.state or "")
            profile.city = data.get("city", profile.city or "")
            profile.timezone = data.get("timezone", profile.timezone or "")
            profile.profile_picture = data.get("profile_picture", profile.profile_picture or "")

        elif step == 2:
            UserEducation.query.filter_by(user_id=uid).delete()
            status = data.get("status", "student")
            college = data.get("college", "").strip()
            degree = data.get("degree", "").strip()
            if college and degree:
                edu = UserEducation(
                    user_id=uid,
                    institution=college,
                    degree=degree,
                    branch=data.get("branch", ""),
                    graduation_year=data.get("grad_year"),
                    current_semester=data.get("semester"),
                    cgpa=data.get("cgpa"),
                    order=0,
                )
                db.session.add(edu)
            cp = _get_or_create_career_profile(uid)
            cp.career_level = status

        elif step == 3:
            cp = _get_or_create_career_profile(uid)
            cp.position = data.get("current_role", cp.position or "")
            cp.target_role = data.get("dream_role", cp.target_role or "")
            cp.years_experience = data.get("experience", cp.years_experience or 0)
            cp.preferred_industry = data.get("industry", cp.preferred_industry or "")
            cp.employment_type = data.get("employment_status", cp.employment_type or "")
            cp.target_salary = data.get("salary", cp.target_salary or "")
            cp.preferred_country = data.get("country", cp.preferred_country or "")
            cp.work_preference = data.get("work_preference", cp.work_preference or "remote")

        elif step == 4:
            UserSkill.query.filter_by(user_id=uid).delete()
            skills_list = data.get("skills", [])
            for item in skills_list:
                name = (item.get("name", "") if isinstance(item, dict) else str(item)).strip()
                if name:
                    db.session.add(UserSkill(user_id=uid, name=name))

        elif step == 5:
            UserInterest.query.filter_by(user_id=uid).delete()
            interests_list = data.get("interests", [])
            for item in interests_list:
                name = (item.get("name", "") if isinstance(item, dict) else str(item)).strip()
                if name:
                    db.session.add(UserInterest(user_id=uid, name=name, is_custom=True))

        elif step == 6:
            CareerGoal.query.filter_by(user_id=uid).delete()
            goals_list = data.get("goals", [])
            for item in goals_list:
                title = (item.get("title", "") if isinstance(item, dict) else str(item)).strip()
                if title:
                    db.session.add(CareerGoal(
                        user_id=uid,
                        title=title,
                        target_role=item.get("target_role", "") if isinstance(item, dict) else "",
                        target_company=item.get("target_company", "") if isinstance(item, dict) else "",
                        status=item.get("status", "active") if isinstance(item, dict) else "active",
                        priority=item.get("priority", 3) if isinstance(item, dict) else 3,
                        category=item.get("category", "career") if isinstance(item, dict) else "career",
                    ))

        elif step == 7:
            pass

        elif step == 8:
            pref = _get_or_create_preferences(uid)
            pref.ai_tone = data.get("ai_tone", pref.ai_tone or "professional")
            pref.reminder_freq = data.get("reminder_freq", pref.reminder_freq or "weekly")
            if "weekly_reports" in data:
                pref.weekly_reports = bool(data["weekly_reports"])
            if "roadmap_gen" in data:
                pref.roadmap_gen = bool(data["roadmap_gen"])
            if "daily_motivation" in data:
                pref.daily_motivation = bool(data["daily_motivation"])

        else:
            return jsonify({"error": f"Invalid step: {step}"}), 400

        if step > (current_user.onboarding_step or 0) and step <= TOTAL_STEPS:
            current_user.onboarding_step = step

        db.session.commit()
        return jsonify({
            "message": f"Step {step} saved",
            "onboarding_step": current_user.onboarding_step,
            "step_label": STEP_LABELS.get(current_user.onboarding_step or 0, ""),
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Failed to save step %s: %s", step, str(e), exc_info=True)
        return jsonify({"error": f"Failed to save step {step}", "reason": str(e)}), 500


@onboarding_bp.route("/api/onboarding/complete", methods=["POST"])
@login_required
def complete_onboarding():
    current_user.onboarding_completed = True
    current_user.onboarding_step = TOTAL_STEPS
    db.session.commit()
    return jsonify({"message": "Onboarding completed"}), 200


@onboarding_bp.route("/api/onboarding/reset", methods=["POST"])
@login_required
def reset_onboarding():
    try:
        current_user.onboarding_completed = False
        current_user.onboarding_step = 0
        db.session.commit()
        return jsonify({"message": "Onboarding reset"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
