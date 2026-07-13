import logging

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.core.session import safe_commit
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


STAGE_LABELS = {
    "student": "Student",
    "fresher": "Fresher / Recent Graduate",
    "professional": "Working Professional",
    "switcher": "Career Switcher",
}

STEP_LABELS = {
    0: "Welcome",
    1: "Basic Info",
    2: "Career Stage",
    3: "Skills",
    4: "Interests & Goals",
    5: "Connect",
    6: "AI Preferences",
}

TOTAL_STEPS = 6


@onboarding_bp.route("/api/onboarding/status", methods=["GET"])
@login_required
def get_status():
    cp = CareerProfile.query.filter_by(user_id=current_user.id).first()
    return jsonify({
        "onboarding_completed": current_user.onboarding_completed or False,
        "onboarding_step": current_user.onboarding_step or 0,
        "total_steps": TOTAL_STEPS,
        "step_label": STEP_LABELS.get(current_user.onboarding_step or 0, "Welcome"),
        "career_stage": cp.career_stage if cp else "student",
    }), 200


@onboarding_bp.route("/api/onboarding/step/<int:step>", methods=["GET"])
@login_required
def get_step(step):
    uid = current_user.id
    data = {}
    try:
        cp = CareerProfile.query.filter_by(user_id=uid).first()
        stage = cp.career_stage if cp else "student"
        stage_meta = cp.stage_meta or {} if cp else {}

        if step == 1:
            profile = Profile.query.filter_by(user_id=uid).first()
            resume = Resume.query.filter_by(user_id=uid).first()
            data = {
                "full_name": resume.full_name if resume else "",
                "date_of_birth": profile.date_of_birth if profile else "",
                "country": profile.country if profile else "",
                "state": profile.state if profile else "",
                "city": profile.city if profile else "",
                "timezone": profile.timezone if profile else "",
            }
        elif step == 2:
            edu = UserEducation.query.filter_by(user_id=uid).order_by(UserEducation.order).first()
            data = {
                "career_stage": stage,
                "college": edu.institution if edu else "",
                "degree": edu.degree if edu else "",
                "branch": edu.branch if edu else "",
                "grad_year": edu.graduation_year if edu else None,
                "current_semester": edu.current_semester if edu else None,
                "cgpa": edu.cgpa if edu else None,
                "internship_experience": cp.position if cp and stage == "fresher" else "",
                "projects": stage_meta.get("projects", []),
                "certifications": stage_meta.get("certifications", []),
                "current_company": cp.company if cp else "",
                "current_role": cp.position if cp else "",
                "industry": cp.preferred_industry if cp else "",
                "years_experience": cp.years_experience if cp else 0,
                "current_ctc": stage_meta.get("current_ctc", ""),
                "expected_ctc": stage_meta.get("expected_ctc", ""),
                "notice_period": stage_meta.get("notice_period", ""),
                "dream_role": cp.target_role if cp else "",
                "preferred_country": cp.preferred_country if cp else "",
                "work_preference": cp.work_preference if cp else "remote",
                "employment_type": cp.employment_type if cp else "",
                "preferred_internship": stage_meta.get("preferred_internship", ""),
                "current_profession": stage_meta.get("current_profession", ""),
                "target_profession": stage_meta.get("target_profession", ""),
                "transferable_skills": stage_meta.get("transferable_skills", []),
                "learning_progress": stage_meta.get("learning_progress", ""),
                "career_goals_text": stage_meta.get("career_goals_text", ""),
                "expected_salary": stage_meta.get("expected_salary", ""),
                "github_url": stage_meta.get("github_url", ""),
                "linkedin_url": stage_meta.get("linkedin_url", ""),
            }
        elif step == 3:
            skills = UserSkill.query.filter_by(user_id=uid).order_by(UserSkill.name).all()
            data = {"skills": [{"name": s.name} for s in skills]}
        elif step == 4:
            interests = UserInterest.query.filter_by(user_id=uid).all()
            goals = CareerGoal.query.filter_by(user_id=uid).all()
            data = {
                "interests": [{"name": i.name} for i in interests],
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
                ],
            }
        elif step == 5:
            from app.integrations.models import Integration
            integrations = Integration.query.filter_by(user_id=uid).all()
            data = {
                "connected": {i.provider: True for i in integrations},
                "providers": [i.provider for i in integrations],
            }
        elif step == 6:
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
        return jsonify({"error": f"Failed to load step {step}"}), 500


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

        elif step == 2:
            cp = _get_or_create_career_profile(uid)
            stage = data.get("career_stage", "student")
            cp.career_stage = stage

            if stage == "student":
                UserEducation.query.filter_by(user_id=uid).delete()
                college = data.get("college", "").strip()
                degree = data.get("degree", "").strip()
                if college and degree:
                    edu = UserEducation(
                        user_id=uid,
                        institution=college,
                        degree=degree,
                        branch=data.get("branch", ""),
                        graduation_year=data.get("grad_year"),
                        current_semester=data.get("current_semester"),
                        cgpa=data.get("cgpa"),
                        order=0,
                    )
                    db.session.add(edu)
                cp.target_role = data.get("dream_role", cp.target_role or "")
                cp.preferred_country = data.get("preferred_country", cp.preferred_country or "")
                cp.stage_meta = {
                    "preferred_internship": data.get("preferred_internship", ""),
                    "github_url": data.get("github_url", ""),
                    "linkedin_url": data.get("linkedin_url", ""),
                }

            elif stage == "fresher":
                UserEducation.query.filter_by(user_id=uid).delete()
                college = data.get("college", "").strip()
                if college:
                    edu = UserEducation(
                        user_id=uid,
                        institution=college,
                        degree=data.get("degree", ""),
                        graduation_year=data.get("grad_year"),
                        order=0,
                    )
                    db.session.add(edu)
                cp.position = data.get("internship_experience", cp.position or "")
                cp.target_role = data.get("dream_role", cp.target_role or "")
                cp.preferred_country = data.get("preferred_country", cp.preferred_country or "")
                cp.stage_meta = {
                    "projects": data.get("projects", []),
                    "certifications": data.get("certifications", []),
                    "expected_salary": data.get("expected_salary", ""),
                }

            elif stage == "professional":
                cp.company = data.get("current_company", cp.company or "")
                cp.position = data.get("current_role", cp.position or "")
                cp.preferred_industry = data.get("industry", cp.preferred_industry or "")
                cp.years_experience = data.get("years_experience", cp.years_experience or 0)
                cp.target_role = data.get("dream_role", cp.target_role or "")
                cp.preferred_country = data.get("preferred_country", cp.preferred_country or "")
                cp.work_preference = data.get("work_preference", cp.work_preference or "remote")
                cp.employment_type = data.get("employment_type", cp.employment_type or "")
                cp.stage_meta = {
                    "current_ctc": data.get("current_ctc", ""),
                    "expected_ctc": data.get("expected_ctc", ""),
                    "notice_period": data.get("notice_period", ""),
                }

            elif stage == "switcher":
                cp.target_role = data.get("target_profession", cp.target_role or "")
                cp.preferred_country = data.get("preferred_country", cp.preferred_country or "")
                cp.stage_meta = {
                    "current_profession": data.get("current_profession", ""),
                    "target_profession": data.get("target_profession", ""),
                    "transferable_skills": data.get("transferable_skills", []),
                    "learning_progress": data.get("learning_progress", ""),
                    "career_goals_text": data.get("career_goals_text", ""),
                }

        elif step == 3:
            UserSkill.query.filter_by(user_id=uid).delete()
            skills_list = data.get("skills", [])
            for item in skills_list:
                name = (item.get("name", "") if isinstance(item, dict) else str(item)).strip()
                if name:
                    db.session.add(UserSkill(user_id=uid, name=name))

        elif step == 4:
            UserInterest.query.filter_by(user_id=uid).delete()
            interests_list = data.get("interests", [])
            for item in interests_list:
                name = (item.get("name", "") if isinstance(item, dict) else str(item)).strip()
                if name:
                    db.session.add(UserInterest(user_id=uid, name=name, is_custom=True))

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

        elif step == 5:
            pass

        elif step == 6:
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

        safe_commit()

        from app.core.integration import on_profile_changed
        on_profile_changed(uid)

        return jsonify({
            "message": f"Step {step} saved",
            "onboarding_step": current_user.onboarding_step,
            "step_label": STEP_LABELS.get(current_user.onboarding_step or 0, ""),
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Failed to save step %s: %s", step, str(e), exc_info=True)
        return jsonify({"error": f"Failed to save step {step}"}), 500


@onboarding_bp.route("/api/onboarding/complete", methods=["POST"])
@login_required
def complete_onboarding():
    current_user.onboarding_completed = True
    current_user.onboarding_step = TOTAL_STEPS
    safe_commit()
    from app.core.integration import on_profile_changed
    on_profile_changed(current_user.id)
    return jsonify({"message": "Onboarding completed"}), 200


@onboarding_bp.route("/api/onboarding/reset", methods=["POST"])
@login_required
def reset_onboarding():
    try:
        current_user.onboarding_completed = False
        current_user.onboarding_step = 0
        safe_commit()
        return jsonify({"message": "Onboarding reset"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error("Failed to reset onboarding: %s", str(e), exc_info=True)
        return jsonify({"error": "Failed to reset onboarding"}), 500
