from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.core.session import safe_commit
from app.users.models import Profile

users_bp = Blueprint("users", __name__)


@users_bp.route("/ping")
def ping():
    return {"blueprint": "users", "status": "alive"}


@users_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    from app.resume.models import Resume

    profile = Profile.query.filter_by(user_id=current_user.id).first()
    resume = Resume.query.filter_by(user_id=current_user.id).first()

    if not profile and not resume:
        return jsonify({"profile": None}), 200

    data = {
        "email": current_user.email,
    }

    if profile:
        data.update(
            {
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
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "phone_number": profile.phone_number,
                "date_of_birth": profile.date_of_birth,
                "gender": profile.gender,
                "state": profile.state,
                "city": profile.city,
                "timezone": profile.timezone,
                "profile_picture": profile.profile_picture,
                "career_summary": profile.career_summary,
                "username": profile.username,
                "language": profile.language,
                "date_format": profile.date_format,
            }
        )

    if resume:
        data.update(
            {
                "full_name": resume.full_name,
                "phone": resume.phone,
                "location": resume.location,
                "title": resume.title,
                "website": resume.website,
                "linkedin": resume.linkedin,
                "github": resume.github,
            }
        )

    return jsonify({"profile": data}), 200


@users_bp.route("/profile", methods=["POST", "PUT"])
@login_required
def upsert_profile():
    from app.resume.models import Resume

    data = request.get_json(silent=True) or {}

    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)

    resume = Resume.query.filter_by(user_id=current_user.id).first()

    profile_fields = [
        "education",
        "degree",
        "graduation_year",
        "country",
        "preferred_roles",
        "skills",
        "experience",
        "languages",
        "interests",
        "preferred_locations",
        "salary_expectation",
        "first_name",
        "last_name",
        "phone_number",
        "date_of_birth",
        "gender",
        "state",
        "city",
        "timezone",
        "profile_picture",
        "career_summary",
        "username",
        "language",
        "date_format",
    ]
    for field in profile_fields:
        if field in data:
            setattr(profile, field, data[field])

    resume_fields = [
        "full_name",
        "phone",
        "location",
        "title",
        "website",
        "linkedin",
        "github",
    ]
    if not resume:
        resume = Resume(user_id=current_user.id)
        db.session.add(resume)
    for field in resume_fields:
        if field in data:
            setattr(resume, field, data[field])

    safe_commit()

    from app.core.integration import on_profile_changed
    on_profile_changed(current_user.id)

    return jsonify({"message": "Profile saved successfully"}), 200


@users_bp.route("/dashboard-summary", methods=["GET"])
@login_required
def dashboard_summary():
    from app.resume.models import Resume, ResumeVersion
    from app.jobs.models import Job
    from app.coach.models import CoachMessage
    from app.users.models import Profile
    from datetime import date

    profile = Profile.query.filter_by(user_id=current_user.id).first()
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    jobs = Job.query.filter_by(user_id=current_user.id).all()

    resume_versions = []
    resume_versions_count = 0
    if resume:
        versions = (
            ResumeVersion.query.filter_by(resume_id=resume.id)
            .order_by(ResumeVersion.created_at.desc())
            .all()
        )
        resume_versions_count = len(versions)
        if versions:
            v = versions[0]
            resume_versions = {
                "count": resume_versions_count,
                "latest": {
                    "id": v.id,
                    "version_name": v.version_name,
                    "source": v.source or "manual",
                    "ats_score": v.ats_score,
                    "updated_at": v.updated_at.isoformat() if v.updated_at else None,
                }
            }

    active_statuses = ["applied", "oa", "interview"]
    active_applications = len([j for j in jobs if j.status in active_statuses])
    offers = len([j for j in jobs if j.status == "offer"])

    profile_fields = [
        "education",
        "degree",
        "graduation_year",
        "country",
        "preferred_roles",
        "skills",
        "experience",
        "languages",
        "interests",
        "preferred_locations",
        "salary_expectation",
    ]
    filled = (
        sum(1 for f in profile_fields if getattr(profile, f, None)) if profile else 0
    )
    profile_completeness = round((filled / len(profile_fields)) * 100) if profile else 0

    jobs_by_status = {}
    for j in jobs:
        s = j.status
        jobs_by_status[s] = jobs_by_status.get(s, 0) + 1

    upcoming_deadlines = sorted(
        [
            {
                "company": j.company,
                "role": j.role,
                "deadline": j.deadline.isoformat(),
                "id": j.id,
                "status": j.status,
            }
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

    recent_activity = []

    for job in sorted(jobs, key=lambda j: j.updated_at or j.created_at, reverse=True)[
        :5
    ]:
        desc = (
            f"Applied to {job.company} for {job.role}"
            if job.status == "applied"
            else f"{job.status.capitalize()} at {job.company} for {job.role}"
        )
        recent_activity.append(
            {
                "type": "job",
                "description": desc,
                "timestamp": (job.updated_at or job.created_at).isoformat(),
                "metadata": {
                    "job_id": job.id,
                    "status": job.status,
                    "company": job.company,
                    "role": job.role,
                },
            }
        )

    recent_messages = (
        CoachMessage.query.filter_by(user_id=current_user.id, role="user")
        .order_by(CoachMessage.created_at.desc())
        .limit(3)
        .all()
    )
    for msg in recent_messages:
        preview = msg.content[:80] + ("..." if len(msg.content) > 80 else "")
        recent_activity.append(
            {
                "type": "coach",
                "description": f"Chatted about: {preview}",
                "timestamp": msg.created_at.isoformat(),
                "metadata": {},
            }
        )

    if resume and resume.updated_at:
        recent_activity.append(
            {
                "type": "resume",
                "description": "Updated your resume",
                "timestamp": resume.updated_at.isoformat(),
                "metadata": {},
            }
        )

    recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
    recent_activity = recent_activity[:10]

    return jsonify(
        {
            "email": current_user.email,
            "name": resume.full_name
            if resume and resume.full_name
            else current_user.email.split("@")[0],
            "has_resume": resume is not None,
            "resume_summary_set": bool(resume and resume.summary),
            "resume_versions": resume_versions,
            "profile_completeness": profile_completeness,
            "resume_skills": resume.skills if resume and resume.skills is not None else [],
            "active_applications": active_applications,
            "offers": offers,
            "total_applications": len(jobs),
            "jobs_by_status": jobs_by_status,
            "upcoming_deadlines": upcoming_deadlines,
            "last_coach_message": last_message.content if last_message else None,
            "last_coach_message_at": last_message.created_at.isoformat()
            if last_message
            else None,
            "recent_activity": recent_activity,
        }
    ), 200


@users_bp.route("/notifications", methods=["GET"])
@login_required
def get_notification_preferences():
    from app.career.models import UserPreference

    prefs = UserPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        return jsonify({"preferences": {}}), 200
    return jsonify({
        "preferences": {
            "email_notifications": prefs.email_notifications,
            "push_notifications": True,
            "ai_weekly_review": prefs.weekly_ai_review,
            "career_reminders": prefs.job_alerts,
            "interview_reminders": prefs.reminder_freq != "never",
            "goal_reminders": prefs.weekly_reports,
            "marketing_emails": prefs.daily_motivation,
        }
    }), 200


@users_bp.route("/notifications", methods=["POST"])
@login_required
def save_notification_preferences():
    from app.career.models import UserPreference

    data = request.get_json(silent=True) or {}
    prefs_in = data.get("preferences", {})

    prefs = UserPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.session.add(prefs)

    if "email_notifications" in prefs_in:
        prefs.email_notifications = bool(prefs_in["email_notifications"])
    if "ai_weekly_review" in prefs_in:
        prefs.weekly_ai_review = bool(prefs_in["ai_weekly_review"])
    if "career_reminders" in prefs_in:
        prefs.job_alerts = bool(prefs_in["career_reminders"])
    if "goal_reminders" in prefs_in:
        prefs.weekly_reports = bool(prefs_in["goal_reminders"])
    if "marketing_emails" in prefs_in:
        prefs.daily_motivation = bool(prefs_in["marketing_emails"])
    if "interview_reminders" in prefs_in:
        prefs.reminder_freq = "daily" if prefs_in["interview_reminders"] else "never"

    safe_commit()
    return jsonify({"message": "Notification preferences saved"}), 200


@users_bp.route("/ai-preferences", methods=["GET"])
@login_required
def get_ai_preferences():
    from app.career.models import UserPreference

    prefs = UserPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        return jsonify({"preferences": {}}), 200
    return jsonify({
        "preferences": {
            "default_model": "gpt-4",
            "response_style": "balanced",
            "coaching_mode": prefs.ai_tone or "encouraging",
            "interview_difficulty": "medium",
            "roadmap_detail": "detailed",
            "auto_suggestions": prefs.weekly_reports,
        }
    }), 200


@users_bp.route("/ai-preferences", methods=["POST"])
@login_required
def save_ai_preferences():
    from app.career.models import UserPreference

    data = request.get_json(silent=True) or {}
    prefs_in = data.get("preferences", {})

    prefs = UserPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.session.add(prefs)

    if "coaching_mode" in prefs_in:
        prefs.ai_tone = prefs_in["coaching_mode"]

    safe_commit()
    return jsonify({"message": "AI preferences saved"}), 200


@users_bp.route("/export", methods=["GET"])
@login_required
def export_user_data():
    from app.career.models import UserPreference

    profile = Profile.query.filter_by(user_id=current_user.id).first()
    prefs = UserPreference.query.filter_by(user_id=current_user.id).first()
    return jsonify({
        "user": {"id": current_user.id, "email": current_user.email},
        "profile": {
            k: getattr(profile, k, None)
            for k in [
                "first_name", "last_name", "username", "phone_number", "country",
                "state", "city", "skills", "experience", "education", "languages",
                "interests", "preferred_roles", "preferred_locations",
                "career_summary", "profile_picture",
            ]
        } if profile else None,
        "preferences": {
            "email_notifications": prefs.email_notifications,
            "weekly_ai_review": prefs.weekly_ai_review,
            "job_alerts": prefs.job_alerts,
        } if prefs else {},
    }), 200


@users_bp.route("/career-overview", methods=["GET"])
@login_required
def career_overview():
    from app.resume.models import Resume
    from app.jobs.models import Job

    resume = Resume.query.filter_by(user_id=current_user.id).first()
    jobs = Job.query.filter_by(user_id=current_user.id).all()

    milestones = []
    skills_set = set()

    if resume:
        for exp in resume.experience or []:
            milestones.append(
                {
                    "type": "experience",
                    "title": f"{exp.get('role', 'Role')} at {exp.get('company', 'Company')}",
                    "subtitle": exp.get("company", ""),
                    "date": f"{exp.get('start', '')} - {exp.get('end', 'Present')}",
                }
            )
            tech = exp.get("technologies", "")
            if isinstance(tech, list):
                skills_set.update(t.lower() for t in tech)

        for edu in resume.education or []:
            milestones.append(
                {
                    "type": "education",
                    "title": f"{edu.get('degree', 'Degree')} in {edu.get('field', '')}",
                    "subtitle": edu.get("school", ""),
                    "date": f"{edu.get('start', '')} - {edu.get('end', '')}",
                }
            )

        for cert in resume.certificates or []:
            milestones.append(
                {
                    "type": "certificate",
                    "title": cert.get("name", "Certificate"),
                    "subtitle": cert.get("issuer", ""),
                    "date": cert.get("date", ""),
                }
            )

        for ach in resume.achievements or []:
            milestones.append(
                {
                    "type": "achievement",
                    "title": ach
                    if isinstance(ach, str)
                    else ach.get("title", "Achievement"),
                    "subtitle": ach.get("description", "")
                    if isinstance(ach, dict)
                    else "",
                    "date": ach.get("date", "") if isinstance(ach, dict) else "",
                }
            )

        if resume.skills:
            skills_set.update(s.lower() for s in resume.skills)

    for job in jobs:
        milestones.append(
            {
                "type": "application",
                "title": f"{job.role} at {job.company}",
                "subtitle": f"Status: {job.status}",
                "date": (job.updated_at or job.created_at).strftime("%Y-%m-%d")
                if (job.updated_at or job.created_at)
                else "",
            }
        )

    milestones.sort(key=lambda m: m.get("date", ""), reverse=True)

    total_roles = (
        len(
            set(
                (e.get("company", ""), e.get("role", ""))
                for e in (resume.experience or [])
            )
        )
        if resume
        else 0
    )

    years_set = set()
    for m in milestones:
        d = m.get("date", "")
        if d and len(d) >= 4:
            for part in d.replace(" - ", "-").split("-"):
                part = part.strip()
                if part.isdigit() and len(part) == 4:
                    years_set.add(int(part))
    years_active = len(years_set) if years_set else 0

    return jsonify(
        {
            "full_name": resume.full_name
            if resume
            else current_user.email.split("@")[0],
            "milestones": milestones[:50],
            "years_active": years_active,
            "total_roles": total_roles,
            "skills_gained": sorted(skills_set),
            "top_achievement": resume.achievements[0]
            if resume and resume.achievements
            else None,
        }
    ), 200
