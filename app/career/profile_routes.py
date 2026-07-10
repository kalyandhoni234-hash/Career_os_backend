import logging
import os
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.career.models import (
    UserEducation, UserSkill, UserInterest, UserLanguage,
    SocialLink, ResumeFile, UserPreference, CareerProfile,
    CareerGoal, CareerTimelineEvent,
)
from app.users.models import Profile

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__)


def _basic_info_data(user_id):
    profile = Profile.query.filter_by(user_id=user_id).first()
    user = current_user
    data = {}
    if profile:
        data.update({
            "first_name": getattr(profile, "first_name", ""),
            "last_name": getattr(profile, "last_name", ""),
            "phone_number": getattr(profile, "phone_number", ""),
            "date_of_birth": getattr(profile, "date_of_birth", None),
            "gender": getattr(profile, "gender", ""),
            "country": profile.country or "",
            "state": getattr(profile, "state", ""),
            "city": getattr(profile, "city", ""),
            "timezone": getattr(profile, "timezone", ""),
            "profile_picture": getattr(profile, "profile_picture", ""),
        })
    data["email"] = user.email or ""
    return data


def _education_data(user_id):
    records = UserEducation.query.filter_by(user_id=user_id).order_by(UserEducation.order).all()
    return [
        {
            "id": r.id, "institution": r.institution, "degree": r.degree,
            "branch": r.branch, "specialization": r.specialization,
            "graduation_year": r.graduation_year, "current_semester": r.current_semester,
            "cgpa": r.cgpa, "relevant_coursework": r.relevant_coursework or [],
            "achievements": r.achievements, "order": r.order,
        }
        for r in records
    ]


def _career_info_data(user_id):
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    if not cp:
        return {}
    return {
        "current_status": cp.career_level or "",
        "company": getattr(cp, "company", ""),
        "position": getattr(cp, "position", ""),
        "experience_years": cp.years_experience or 0,
        "employment_type": getattr(cp, "employment_type", ""),
    }


def _dream_career_data(user_id):
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    if not cp:
        return {}
    return {
        "dream_role": cp.target_role or "",
        "dream_company": cp.target_company or "",
        "preferred_industry": getattr(cp, "preferred_industry", ""),
        "preferred_country": getattr(cp, "preferred_country", ""),
        "work_preference": getattr(cp, "work_preference", ""),
        "salary_goal": cp.target_salary or "",
        "target_joining_year": getattr(cp, "target_joining_year", None),
    }


def _skills_data(user_id):
    skills = UserSkill.query.filter_by(user_id=user_id).order_by(UserSkill.name).all()
    return [
        {
            "id": s.id, "name": s.name, "experience_level": s.experience_level,
            "years_of_experience": s.years_of_experience, "confidence_rating": s.confidence_rating,
        }
        for s in skills
    ]


def _interests_data(user_id):
    interests = UserInterest.query.filter_by(user_id=user_id).all()
    return [{"id": i.id, "name": i.name, "is_custom": i.is_custom} for i in interests]


def _languages_data(user_id):
    languages = UserLanguage.query.filter_by(user_id=user_id).all()
    return [{"id": l.id, "language": l.language, "proficiency": l.proficiency} for l in languages]


def _social_links_data(user_id):
    links = SocialLink.query.filter_by(user_id=user_id).all()
    return [{"id": l.id, "platform": l.platform, "url": l.url} for l in links]


def _resume_files_data(user_id):
    files = ResumeFile.query.filter_by(user_id=user_id, is_active=True).order_by(ResumeFile.uploaded_at.desc()).all()
    return [
        {
            "id": f.id, "filename": f.filename, "original_filename": f.original_filename,
            "file_size": f.file_size, "file_type": f.file_type,
            "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
        }
        for f in files
    ]


def _preferences_data(user_id):
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        return {}
    return {
        "job_alerts": pref.job_alerts,
        "weekly_ai_review": pref.weekly_ai_review,
        "email_notifications": pref.email_notifications,
        "public_profile": pref.public_profile,
        "resume_visibility": pref.resume_visibility,
        "theme_preference": pref.theme_preference,
    }


def _completion_pct(user_id):
    score = 0
    total = 0

    profile = Profile.query.filter_by(user_id=user_id).first()
    total += 4
    if profile:
        if profile.country: score += 1
        if getattr(profile, "first_name", None): score += 1
        if getattr(profile, "phone_number", None): score += 1
        if getattr(profile, "city", None): score += 1

    total += 2
    if UserEducation.query.filter_by(user_id=user_id).count() > 0:
        score += 2

    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    total += 2
    if cp:
        if cp.career_level: score += 1
        if cp.years_experience: score += 1

    total += 2
    if cp:
        if cp.target_role: score += 1
        if cp.target_company: score += 1

    total += 2
    if UserSkill.query.filter_by(user_id=user_id).count() > 0:
        score += 2

    total += 1
    if UserInterest.query.filter_by(user_id=user_id).count() > 0:
        score += 1

    total += 1
    if UserLanguage.query.filter_by(user_id=user_id).count() > 0:
        score += 1

    total += 1
    if SocialLink.query.filter_by(user_id=user_id).count() > 0:
        score += 1

    total += 1
    if ResumeFile.query.filter_by(user_id=user_id).count() > 0:
        score += 1

    total += 1
    if UserPreference.query.filter_by(user_id=user_id).first():
        score += 1

    if total == 0:
        return 0
    return round((score / total) * 100)


# ── Wizard: Get all steps ──────────────────────────────────

@profile_bp.route("/api/profile/wizard", methods=["GET"])
@login_required
def get_wizard():
    uid = current_user.id
    data = {
        "basic_info": _basic_info_data(uid),
        "education": _education_data(uid),
        "career_info": _career_info_data(uid),
        "dream_career": _dream_career_data(uid),
        "skills": _skills_data(uid),
        "interests": _interests_data(uid),
        "languages": _languages_data(uid),
        "social_links": _social_links_data(uid),
        "resume_files": _resume_files_data(uid),
        "preferences": _preferences_data(uid),
        "completion_pct": _completion_pct(uid),
    }
    return jsonify(data), 200


# ── Wizard: Save step ──────────────────────────────────────

@profile_bp.route("/api/profile/wizard/<step>", methods=["PUT"])
@login_required
def save_wizard_step(step):
    uid = current_user.id
    data = request.get_json(silent=True) or {}

    try:
        if step == "basic_info":
            profile = Profile.query.filter_by(user_id=uid).first()
            if not profile:
                profile = Profile(user_id=uid)
                db.session.add(profile)
            profile.first_name = data.get("first_name", getattr(profile, "first_name", ""))
            profile.last_name = data.get("last_name", getattr(profile, "last_name", ""))
            profile.phone_number = data.get("phone_number", getattr(profile, "phone_number", ""))
            profile.date_of_birth = data.get("date_of_birth", getattr(profile, "date_of_birth", None))
            profile.gender = data.get("gender", getattr(profile, "gender", ""))
            profile.country = data.get("country", profile.country or "")
            profile.state = data.get("state", getattr(profile, "state", ""))
            profile.city = data.get("city", getattr(profile, "city", ""))
            profile.timezone = data.get("timezone", getattr(profile, "timezone", ""))
            profile.profile_picture = data.get("profile_picture", getattr(profile, "profile_picture", ""))
            if current_user.email != data.get("email", current_user.email):
                current_user.email = data.get("email", current_user.email)
            db.session.commit()

        elif step == "career_info":
            cp = CareerProfile.query.filter_by(user_id=uid).first()
            if not cp:
                cp = CareerProfile(user_id=uid)
                db.session.add(cp)
            cp.career_level = data.get("current_status", cp.career_level or "student")
            cp.company = data.get("company", getattr(cp, "company", ""))
            cp.position = data.get("position", getattr(cp, "position", ""))
            cp.years_experience = data.get("experience_years", cp.years_experience or 0)
            cp.employment_type = data.get("employment_type", getattr(cp, "employment_type", ""))
            db.session.commit()

        elif step == "dream_career":
            cp = CareerProfile.query.filter_by(user_id=uid).first()
            if not cp:
                cp = CareerProfile(user_id=uid)
                db.session.add(cp)
            cp.target_role = data.get("dream_role", cp.target_role or "")
            cp.target_company = data.get("dream_company", cp.target_company or "")
            cp.preferred_industry = data.get("preferred_industry", getattr(cp, "preferred_industry", ""))
            cp.preferred_country = data.get("preferred_country", getattr(cp, "preferred_country", ""))
            cp.work_preference = data.get("work_preference", getattr(cp, "work_preference", ""))
            cp.target_salary = data.get("salary_goal", cp.target_salary or "")
            cp.target_joining_year = data.get("target_joining_year", getattr(cp, "target_joining_year", None))
            db.session.commit()

        elif step == "preferences":
            pref = UserPreference.query.filter_by(user_id=uid).first()
            if not pref:
                pref = UserPreference(user_id=uid)
                db.session.add(pref)
            for field in ["job_alerts", "weekly_ai_review", "email_notifications", "public_profile"]:
                if field in data:
                    setattr(pref, field, data[field])
            for field in ["resume_visibility", "theme_preference"]:
                if field in data:
                    setattr(pref, field, data[field])
            db.session.commit()

        else:
            return jsonify({"error": f"Unknown step: {step}"}), 400

        return jsonify({"message": "Step saved", "completion_pct": _completion_pct(uid)}), 200

    except Exception as e:
        db.session.rollback()
        logger.error("Failed to save wizard step %s for user %s: %s", step, uid, str(e), exc_info=True)
        return jsonify({"error": f"Failed to save {step}", "reason": str(e)}), 500


# ── Profile Dashboard ─────────────────────────────────────

@profile_bp.route("/api/profile/dashboard", methods=["GET"])
@login_required
def profile_dashboard():
    uid = current_user.id
    try:
        dashboard = {
            "completion_pct": _completion_pct(uid),
            "basic_info": _basic_info_data(uid),
            "education": _education_data(uid),
            "career_info": _career_info_data(uid),
            "dream_career": _dream_career_data(uid),
            "skills": _skills_data(uid),
            "interests": _interests_data(uid),
            "languages": _languages_data(uid),
            "social_links": _social_links_data(uid),
            "resume_files": _resume_files_data(uid),
            "preferences": _preferences_data(uid),
            "goals": [
                {
                    "id": g.id, "title": g.title, "target_role": g.target_role,
                    "target_company": g.target_company, "progress": g.progress,
                    "status": g.status, "priority": g.priority,
                }
                for g in CareerGoal.query.filter_by(user_id=uid)
                .order_by(CareerGoal.priority.desc()).limit(5).all()
            ],
        }
        return jsonify(dashboard), 200
    except Exception as e:
        logger.error("Profile dashboard failed for user %s: %s", uid, str(e), exc_info=True)
        return jsonify({"error": "Failed to load profile dashboard", "reason": str(e)}), 500


# ── Education CRUD ─────────────────────────────────────────

@profile_bp.route("/api/profile/education", methods=["POST"])
@login_required
def create_education():
    data = request.get_json(silent=True) or {}
    if not data.get("institution") or not data.get("degree"):
        return jsonify({"error": "Institution and degree are required"}), 400
    try:
        max_order = db.session.query(db.func.max(UserEducation.order)).filter_by(user_id=current_user.id).scalar() or 0
        edu = UserEducation(
            user_id=current_user.id,
            institution=data["institution"],
            degree=data["degree"],
            branch=data.get("branch"),
            specialization=data.get("specialization"),
            graduation_year=data.get("graduation_year"),
            current_semester=data.get("current_semester"),
            cgpa=data.get("cgpa"),
            relevant_coursework=data.get("relevant_coursework", []),
            achievements=data.get("achievements"),
            order=max_order + 1,
        )
        db.session.add(edu)
        db.session.commit()
        return jsonify({
            "id": edu.id, "institution": edu.institution, "degree": edu.degree,
            "branch": edu.branch, "specialization": edu.specialization,
            "graduation_year": edu.graduation_year, "current_semester": edu.current_semester,
            "cgpa": edu.cgpa, "relevant_coursework": edu.relevant_coursework or [],
            "achievements": edu.achievements, "order": edu.order,
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@profile_bp.route("/api/profile/education/<int:edu_id>", methods=["PUT"])
@login_required
def update_education(edu_id):
    edu = UserEducation.query.filter_by(id=edu_id, user_id=current_user.id).first()
    if not edu:
        return jsonify({"error": "Education record not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ["institution", "degree", "branch", "specialization", "achievements"]:
        if field in data:
            setattr(edu, field, data[field])
    for field in ["graduation_year", "current_semester", "order"]:
        if field in data:
            setattr(edu, field, data[field])
    if "cgpa" in data:
        edu.cgpa = float(data["cgpa"]) if data["cgpa"] else None
    if "relevant_coursework" in data and isinstance(data["relevant_coursework"], list):
        edu.relevant_coursework = data["relevant_coursework"]
    db.session.commit()
    return jsonify({"message": "Education updated"}), 200


@profile_bp.route("/api/profile/education/<int:edu_id>", methods=["DELETE"])
@login_required
def delete_education(edu_id):
    edu = UserEducation.query.filter_by(id=edu_id, user_id=current_user.id).first()
    if not edu:
        return jsonify({"error": "Education record not found"}), 404
    db.session.delete(edu)
    db.session.commit()
    return jsonify({"message": "Education deleted"}), 200


@profile_bp.route("/api/profile/education/reorder", methods=["PUT"])
@login_required
def reorder_education():
    data = request.get_json(silent=True) or {}
    order_map = data.get("order", {})
    for edu_id, order in order_map.items():
        edu = UserEducation.query.filter_by(id=int(edu_id), user_id=current_user.id).first()
        if edu:
            edu.order = order
    db.session.commit()
    return jsonify({"message": "Reordered"}), 200


# ── Skills CRUD ────────────────────────────────────────────

@profile_bp.route("/api/profile/skills", methods=["POST"])
@login_required
def create_skill():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Skill name is required"}), 400
    existing = UserSkill.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({"error": "Skill already exists"}), 409
    skill = UserSkill(
        user_id=current_user.id,
        name=name,
        experience_level=data.get("experience_level", "beginner"),
        years_of_experience=data.get("years_of_experience", 0),
        confidence_rating=data.get("confidence_rating", 0),
    )
    db.session.add(skill)
    db.session.commit()
    return jsonify({
        "id": skill.id, "name": skill.name, "experience_level": skill.experience_level,
        "years_of_experience": skill.years_of_experience, "confidence_rating": skill.confidence_rating,
    }), 201


@profile_bp.route("/api/profile/skills/<int:skill_id>", methods=["PUT"])
@login_required
def update_skill(skill_id):
    skill = UserSkill.query.filter_by(id=skill_id, user_id=current_user.id).first()
    if not skill:
        return jsonify({"error": "Skill not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ["experience_level", "name"]:
        if field in data:
            setattr(skill, field, data[field])
    if "years_of_experience" in data:
        skill.years_of_experience = float(data["years_of_experience"])
    if "confidence_rating" in data:
        skill.confidence_rating = int(data["confidence_rating"])
    db.session.commit()
    return jsonify({"message": "Skill updated"}), 200


@profile_bp.route("/api/profile/skills/<int:skill_id>", methods=["DELETE"])
@login_required
def delete_skill(skill_id):
    skill = UserSkill.query.filter_by(id=skill_id, user_id=current_user.id).first()
    if not skill:
        return jsonify({"error": "Skill not found"}), 404
    db.session.delete(skill)
    db.session.commit()
    return jsonify({"message": "Skill deleted"}), 200


# ── Interests CRUD ─────────────────────────────────────────

@profile_bp.route("/api/profile/interests", methods=["POST"])
@login_required
def create_interest():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Interest name is required"}), 400
    existing = UserInterest.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({"error": "Interest already exists"}), 409
    interest = UserInterest(
        user_id=current_user.id,
        name=name,
        is_custom=data.get("is_custom", False),
    )
    db.session.add(interest)
    db.session.commit()
    return jsonify({"id": interest.id, "name": interest.name, "is_custom": interest.is_custom}), 201


@profile_bp.route("/api/profile/interests/batch", methods=["PUT"])
@login_required
def batch_interests():
    data = request.get_json(silent=True) or {}
    names = data.get("interests", [])
    if not isinstance(names, list):
        return jsonify({"error": "interests must be a list"}), 400
    UserInterest.query.filter_by(user_id=current_user.id).delete()
    for name in names:
        is_custom = name not in _PRESET_INTERESTS
        db.session.add(UserInterest(user_id=current_user.id, name=name.strip(), is_custom=is_custom))
    db.session.commit()
    return jsonify({"message": "Interests updated"}), 200


_PRESET_INTERESTS = {
    "AI", "Cybersecurity", "Cloud", "Backend", "Frontend",
    "Data Science", "Mobile", "Blockchain", "UI/UX",
    "Open Source", "Startups", "DevOps", "Machine Learning",
    "AR/VR", "Game Development", "IoT", "Quantum Computing",
    "Database Administration", "Network Engineering", "Product Management",
}


@profile_bp.route("/api/profile/interests/<int:interest_id>", methods=["DELETE"])
@login_required
def delete_interest(interest_id):
    interest = UserInterest.query.filter_by(id=interest_id, user_id=current_user.id).first()
    if not interest:
        return jsonify({"error": "Interest not found"}), 404
    db.session.delete(interest)
    db.session.commit()
    return jsonify({"message": "Interest deleted"}), 200


# ── Languages CRUD ─────────────────────────────────────────

@profile_bp.route("/api/profile/languages", methods=["POST"])
@login_required
def create_language():
    data = request.get_json(silent=True) or {}
    language = data.get("language", "").strip()
    if not language:
        return jsonify({"error": "Language is required"}), 400
    existing = UserLanguage.query.filter_by(user_id=current_user.id, language=language).first()
    if existing:
        return jsonify({"error": "Language already exists"}), 409
    lang = UserLanguage(
        user_id=current_user.id,
        language=language,
        proficiency=data.get("proficiency", "intermediate"),
    )
    db.session.add(lang)
    db.session.commit()
    return jsonify({"id": lang.id, "language": lang.language, "proficiency": lang.proficiency}), 201


@profile_bp.route("/api/profile/languages/<int:lang_id>", methods=["PUT"])
@login_required
def update_language(lang_id):
    lang = UserLanguage.query.filter_by(id=lang_id, user_id=current_user.id).first()
    if not lang:
        return jsonify({"error": "Language not found"}), 404
    data = request.get_json(silent=True) or {}
    if "language" in data:
        lang.language = data["language"]
    if "proficiency" in data:
        lang.proficiency = data["proficiency"]
    db.session.commit()
    return jsonify({"message": "Language updated"}), 200


@profile_bp.route("/api/profile/languages/<int:lang_id>", methods=["DELETE"])
@login_required
def delete_language(lang_id):
    lang = UserLanguage.query.filter_by(id=lang_id, user_id=current_user.id).first()
    if not lang:
        return jsonify({"error": "Language not found"}), 404
    db.session.delete(lang)
    db.session.commit()
    return jsonify({"message": "Language deleted"}), 200


# ── Social Links CRUD ──────────────────────────────────────

@profile_bp.route("/api/profile/social-links", methods=["POST"])
@login_required
def create_social_link():
    data = request.get_json(silent=True) or {}
    platform = data.get("platform", "").strip()
    url = data.get("url", "").strip()
    if not platform or not url:
        return jsonify({"error": "Platform and URL are required"}), 400
    existing = SocialLink.query.filter_by(user_id=current_user.id, platform=platform).first()
    if existing:
        existing.url = url
        db.session.commit()
        return jsonify({"message": "Social link updated", "id": existing.id}), 200
    link = SocialLink(user_id=current_user.id, platform=platform, url=url)
    db.session.add(link)
    db.session.commit()
    return jsonify({"id": link.id, "platform": link.platform, "url": link.url}), 201


@profile_bp.route("/api/profile/social-links/<int:link_id>", methods=["PUT"])
@login_required
def update_social_link(link_id):
    link = SocialLink.query.filter_by(id=link_id, user_id=current_user.id).first()
    if not link:
        return jsonify({"error": "Social link not found"}), 404
    data = request.get_json(silent=True) or {}
    if "url" in data:
        link.url = data["url"]
    if "platform" in data:
        link.platform = data["platform"]
    db.session.commit()
    return jsonify({"message": "Social link updated"}), 200


@profile_bp.route("/api/profile/social-links/<int:link_id>", methods=["DELETE"])
@login_required
def delete_social_link(link_id):
    link = SocialLink.query.filter_by(id=link_id, user_id=current_user.id).first()
    if not link:
        return jsonify({"error": "Social link not found"}), 404
    db.session.delete(link)
    db.session.commit()
    return jsonify({"message": "Social link deleted"}), 200


# ── Resume Upload ──────────────────────────────────────────

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"pdf", "docx"}


@profile_bp.route("/api/profile/resume/upload", methods=["POST"])
@login_required
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF and DOCX files are allowed"}), 400

    upload_dir = os.path.join(current_app.root_path, "..", "uploads", "resumes", str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    original_filename = secure_filename(file.filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{original_filename}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    ResumeFile.query.filter_by(user_id=current_user.id).update({"is_active": False})
    resume_file = ResumeFile(
        user_id=current_user.id,
        filename=filename,
        original_filename=original_filename,
        file_size=os.path.getsize(filepath),
        file_type=original_filename.rsplit(".", 1)[1].lower(),
        is_active=True,
    )
    db.session.add(resume_file)
    db.session.commit()

    return jsonify({
        "id": resume_file.id, "filename": resume_file.filename,
        "original_filename": resume_file.original_filename,
        "file_size": resume_file.file_size, "file_type": resume_file.file_type,
        "uploaded_at": resume_file.uploaded_at.isoformat() if resume_file.uploaded_at else None,
    }), 201


@profile_bp.route("/api/profile/resume/<int:file_id>", methods=["DELETE"])
@login_required
def delete_resume(file_id):
    rf = ResumeFile.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not rf:
        return jsonify({"error": "Resume file not found"}), 404
    db.session.delete(rf)
    db.session.commit()
    return jsonify({"message": "Resume deleted"}), 200


# ── Profile Update (generic field setter for dashboard edit) ──

@profile_bp.route("/api/profile/update", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json(silent=True) or {}
    uid = current_user.id
    section = data.get("section", "")
    fields = data.get("fields", {})
    try:
        if section == "basic_info":
            profile = Profile.query.filter_by(user_id=uid).first()
            if not profile:
                profile = Profile(user_id=uid)
                db.session.add(profile)
            for key, val in fields.items():
                if key == "email":
                    current_user.email = val
                else:
                    setattr(profile, key, val)

        elif section == "career_info":
            cp = CareerProfile.query.filter_by(user_id=uid).first()
            if not cp:
                cp = CareerProfile(user_id=uid)
                db.session.add(cp)
            mapping = {"current_status": "career_level", "experience_years": "years_experience"}
            for key, val in fields.items():
                col = mapping.get(key, key)
                setattr(cp, col, val)

        elif section == "dream_career":
            cp = CareerProfile.query.filter_by(user_id=uid).first()
            if not cp:
                cp = CareerProfile(user_id=uid)
                db.session.add(cp)
            mapping = {"dream_role": "target_role", "dream_company": "target_company", "salary_goal": "target_salary"}
            for key, val in fields.items():
                col = mapping.get(key, key)
                setattr(cp, col, val)

        elif section == "preferences":
            pref = UserPreference.query.filter_by(user_id=uid).first()
            if not pref:
                pref = UserPreference(user_id=uid)
                db.session.add(pref)
            for key, val in fields.items():
                setattr(pref, key, val)

        else:
            return jsonify({"error": f"Unknown section: {section}"}), 400

        db.session.commit()
        return jsonify({"message": f"{section} updated", "completion_pct": _completion_pct(uid)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ── Auto Timeline Event Logger ─────────────────────────────

def _log_timeline_event(user_id, event_type, title, description="", importance=1):
    try:
        existing = CareerTimelineEvent.query.filter_by(
            user_id=user_id, event_type=event_type, title=title
        ).first()
        if existing:
            return
        event = CareerTimelineEvent(
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            event_date=datetime.now(timezone.utc),
            importance=importance,
            status="completed",
        )
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning("Failed to log timeline event: %s", e)


def _check_and_log_profile_events(user_id):
    """Auto-log milestone events based on profile state."""
    profile = Profile.query.filter_by(user_id=user_id).first()
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    if profile:
        if profile.first_name or profile.last_name or profile.country:
            _log_timeline_event(user_id, "profile", "Profile Created",
                                "Basic information added to your career profile", 2)
    if cp:
        if cp.target_role:
            _log_timeline_event(user_id, "goal", "Dream Career Selected",
                                f"Target role set to {cp.target_role}", 3)
        if cp.career_level:
            _log_timeline_event(user_id, "career", "Career Status Updated",
                                f"Current status: {cp.career_level}", 2)
    edu_count = UserEducation.query.filter_by(user_id=user_id).count()
    if edu_count > 0:
        last_edu = UserEducation.query.filter_by(user_id=user_id).order_by(UserEducation.created_at.desc()).first()
        _log_timeline_event(user_id, "education", "Education Added",
                            f"{last_edu.degree} at {last_edu.institution}" if last_edu else "Education record added", 2)
    skill_count = UserSkill.query.filter_by(user_id=user_id).count()
    if skill_count > 0:
        _log_timeline_event(user_id, "learning", "Skills Added",
                            f"{skill_count} skill(s) added to your profile", 2)
    resume_count = ResumeFile.query.filter_by(user_id=user_id, is_active=True).count()
    if resume_count > 0:
        _log_timeline_event(user_id, "resume", "Resume Uploaded",
                            "Resume file added to your profile", 3)


# ── Career Readiness Score ─────────────────────────────────

@profile_bp.route("/api/profile/readiness-score", methods=["GET"])
@login_required
def career_readiness_score():
    uid = current_user.id
    try:
        profile = Profile.query.filter_by(user_id=uid).first()
        cp = CareerProfile.query.filter_by(user_id=uid).first()

        profile_score = 0
        pf_total = 0
        for field in ["first_name", "country", "city", "phone_number"]:
            if profile and getattr(profile, field, None):
                profile_score += 1
            pf_total += 1

        edu_score = 0
        edu_count = UserEducation.query.filter_by(user_id=uid).count()
        if edu_count > 0:
            edu_score = min(100, edu_count * 25)

        skill_score = 0
        skill_count = UserSkill.query.filter_by(user_id=uid).count()
        if skill_count > 0:
            skill_score = min(100, skill_count * 12)

        resume_score = 100 if ResumeFile.query.filter_by(user_id=uid, is_active=True).count() > 0 else 0

        project_score = 30
        if resume_score > 0:
            project_score = 60
        if skill_count >= 5:
            project_score = 80
        if edu_count >= 1 and skill_count >= 3:
            project_score = 100

        exp_score = 0
        if cp:
            exp_years = cp.years_experience or 0
            if exp_years >= 5:
                exp_score = 100
            elif exp_years >= 3:
                exp_score = 80
            elif exp_years >= 1:
                exp_score = 60
            elif exp_years > 0:
                exp_score = 40
            elif cp.career_level:
                exp_score = 20

        networking_score = 0
        social_count = SocialLink.query.filter_by(user_id=uid).count()
        networking_score = min(100, social_count * 15)

        weights = {"profile": 15, "education": 20, "skills": 20, "resume": 15, "projects": 10, "experience": 10, "networking": 10}
        overall = (
            (profile_score / max(pf_total, 1)) * 100 * weights["profile"] / 100
            + edu_score * weights["education"] / 100
            + skill_score * weights["skills"] / 100
            + resume_score * weights["resume"] / 100
            + project_score * weights["projects"] / 100
            + exp_score * weights["experience"] / 100
            + networking_score * weights["networking"] / 100
        )

        return jsonify({
            "overall": round(overall),
            "breakdown": {
                "profile": round((profile_score / max(pf_total, 1)) * 100),
                "education": edu_score,
                "skills": skill_score,
                "resume": resume_score,
                "projects": project_score,
                "experience": exp_score,
                "networking": networking_score,
            },
            "weights": weights,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── AI Career Summary ──────────────────────────────────────

@profile_bp.route("/api/profile/career-summary", methods=["GET"])
@login_required
def career_summary():
    uid = current_user.id
    try:
        cp = CareerProfile.query.filter_by(user_id=uid).first()
        profile = Profile.query.filter_by(user_id=uid).first()
        skills = UserSkill.query.filter_by(user_id=uid).all()
        education = UserEducation.query.filter_by(user_id=uid).order_by(UserEducation.graduation_year.desc()).first()

        parts = []
        if education:
            level = education.degree or ""
            field = education.branch or education.specialization or ""
            if level and field:
                parts.append(f"{level} student in {field}")
            elif level:
                parts.append(f"{level} student")

        skill_names = [s.name for s in skills if s.name]
        if skill_names:
            if len(skill_names) > 3:
                parts.append(f"skilled in {', '.join(skill_names[:3])}, and more")
            else:
                parts.append(f"skilled in {', '.join(skill_names)}")

        if cp and cp.target_role:
            parts.append(f"working toward becoming a {cp.target_role}")

        level = ""
        if cp and cp.career_level:
            level_map = {"student": "Currently a student", "intern": "Currently an intern",
                         "fresher": "A recent graduate", "working_professional": "A working professional",
                         "freelancer": "A freelancer", "entrepreneur": "An entrepreneur"}
            level = level_map.get(cp.career_level, "")

        summary = ""
        if parts:
            combined = ", ".join(parts[:-1]) + (f", and {parts[-1]}" if len(parts) > 1 else parts[0])
            summary = combined.capitalize() + "."
        elif level:
            summary = f"{level} exploring career opportunities."
        else:
            summary = ""

        # Also check stored summary in Profile
        stored_summary = getattr(profile, "career_summary", "") or ""

        return jsonify({
            "summary": stored_summary or summary,
            "is_auto_generated": not bool(stored_summary),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@profile_bp.route("/api/profile/career-summary", methods=["PUT"])
@login_required
def save_career_summary():
    data = request.get_json(silent=True) or {}
    summary = data.get("summary", "").strip()
    uid = current_user.id
    profile = Profile.query.filter_by(user_id=uid).first()
    if not profile:
        profile = Profile(user_id=uid)
        db.session.add(profile)
    profile.career_summary = summary
    db.session.commit()
    return jsonify({"message": "Summary saved"}), 200


# ── Smart Recommendations ──────────────────────────────────

@profile_bp.route("/api/profile/smart-recommendations", methods=["GET"])
@login_required
def smart_recommendations():
    uid = current_user.id
    recs = []

    has_resume = ResumeFile.query.filter_by(user_id=uid, is_active=True).count() > 0
    has_education = UserEducation.query.filter_by(user_id=uid).count() > 0
    has_skills = UserSkill.query.filter_by(user_id=uid).count() > 1
    has_social = SocialLink.query.filter_by(user_id=uid).count() > 0
    has_goal = CareerGoal.query.filter_by(user_id=uid, status="active").count() > 0
    has_dream_role = CareerProfile.query.filter_by(user_id=uid).first()
    has_dream = has_dream_role and has_dream_role.target_role and has_dream_role.target_company

    if not has_resume:
        recs.append({"id": "upload_resume", "action": "Upload Resume", "description": "Helps AI analyze your background and match you with opportunities", "icon": "FileText", "priority": 1})
    if not has_education and not has_resume:
        recs.append({"id": "add_education", "action": "Add Education", "description": "Your educational background helps personalize career recommendations", "icon": "GraduationCap", "priority": 2})
    if not has_skills:
        recs.append({"id": "add_skills", "action": "Add Skills", "description": "Skills power your career insights and skill gap analysis", "icon": "Zap", "priority": 3})
    if not has_social:
        recs.append({"id": "connect_github", "action": "Connect GitHub", "description": "Link your GitHub to showcase projects and coding activity", "icon": "Github", "priority": 4})
    if not has_goal:
        recs.append({"id": "create_goal", "action": "Create First Goal", "description": "Goals help Career OS build a personalized roadmap for you", "icon": "Target", "priority": 5})
    if not has_dream:
        recs.append({"id": "set_dream_career", "action": "Set Dream Career", "description": "Define your dream role and company for tailored recommendations", "icon": "Star", "priority": 6})

    return jsonify({"recommendations": recs}), 200
