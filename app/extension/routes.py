"""Chrome Extension API — single endpoint for the extension to submit applications.

When the extension detects a job application:
1. Saves company and job details
2. Creates the application record
3. Calculates fit score against the user's resume
4. Schedules a follow-up reminder
5. Updates all dependent data (dashboard, analytics, recommendations)
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.core.session import safe_commit

logger = logging.getLogger(__name__)

extension_bp = Blueprint("extension", __name__, url_prefix="/api/extension")


@extension_bp.route("/application", methods=["POST"])
@login_required
def create_extension_application():
    """Create a job application from Chrome Extension data."""
    data = request.get_json(silent=True) or {}

    company = (data.get("company") or "").strip()
    role = (data.get("role") or "").strip()

    if not company or not role:
        return jsonify({"error": "Company and role are required"}), 400

    from app.jobs.models import Job
    from app.career.services.skill_graph_service import analyze_skill_gaps

    job_description = (data.get("job_description") or "").strip()
    job_link = (data.get("job_link") or "").strip()
    location = (data.get("location") or "").strip()
    salary = data.get("salary")
    deadline_str = data.get("deadline")

    deadline = None
    if deadline_str:
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Deadline must be in YYYY-MM-DD format"}), 400

    ats_score = None
    fit_score = None

    from app.resume.models import Resume
    resume = Resume.query.filter_by(user_id=current_user.id).first()

    if resume and job_description:
        from app.resume.ats import score_resume
        try:
            ats_result = score_resume(resume, job_description)
            ats_score = ats_result.get("overall_score", 0)
            fit_score = ats_score
        except Exception as e:
            logger.warning("ATS scoring failed for extension application: %s", e)

    job = Job(
        user_id=current_user.id,
        company=company,
        role=role,
        status="applied",
        salary=salary,
        notes=data.get("notes"),
        job_link=job_link,
        deadline=deadline,
        location=location,
        ats_score=ats_score,
        next_action=(datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d"),
    )
    db.session.add(job)
    safe_commit()

    skill_gaps = []
    if job_description:
        try:
            gaps_result = analyze_skill_gaps(current_user.id, target_role=role)
            skill_gaps = gaps_result.get("missing_skills", [])
        except Exception as e:
            logger.warning("Skill gap analysis failed for extension application: %s", e)

    from app.core.integration import on_application_changed
    on_application_changed(current_user.id, job.id)

    from app.career.services.recommendation_service import generate_recommendations
    try:
        generate_recommendations(current_user.id)
    except Exception as e:
        logger.warning("Recommendation generation skipped after extension application: %s", e)

    return jsonify({
        "message": "Application created",
        "job": {
            "id": job.id,
            "company": job.company,
            "role": job.role,
            "status": job.status,
            "ats_score": ats_score,
            "fit_score": fit_score,
            "deadline": deadline.isoformat() if deadline else None,
            "next_action": job.next_action,
        },
        "skill_gaps": skill_gaps[:10],
        "follow_up": (datetime.utcnow() + timedelta(days=7)).isoformat(),
    }), 201
