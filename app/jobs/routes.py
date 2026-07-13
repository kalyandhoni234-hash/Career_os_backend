from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.core.session import safe_commit
from app.jobs.models import Job

jobs_bp = Blueprint("jobs", __name__)

VALID_STATUSES = ["applied", "oa", "interview", "offer", "rejected"]
VALID_PRIORITIES = ["low", "medium", "high"]


def _serialize(job):
    return {
        "id": job.id,
        "company": job.company,
        "role": job.role,
        "status": job.status,
        "salary": job.salary,
        "recruiter": job.recruiter,
        "notes": job.notes,
        "deadline": job.deadline.isoformat() if job.deadline else None,
        "job_link": job.job_link,
        "priority": job.priority or "medium",
        "next_action": job.next_action,
        "resume_version": job.resume_version,
        "ats_score": job.ats_score,
        "location": job.location,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@jobs_bp.route("/ping")
def ping():
    return {"blueprint": "jobs", "status": "alive"}


@jobs_bp.route("", methods=["GET"])
@login_required
def list_jobs():
    jobs = (
        Job.query.filter_by(user_id=current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return jsonify({"jobs": [_serialize(j) for j in jobs]}), 200


@jobs_bp.route("", methods=["POST"])
@login_required
def create_job():
    data = request.get_json(silent=True) or {}

    company = data.get("company", "").strip()
    role = data.get("role", "").strip()

    if not company or not role:
        return jsonify({"error": "Company and role are required"}), 400

    if len(company) > 255:
        return jsonify({"error": "Company name too long (max 255 characters)"}), 400

    if len(role) > 255:
        return jsonify({"error": "Role too long (max 255 characters)"}), 400

    if len(data.get("notes", "") or "") > 5000:
        return jsonify({"error": "Notes too long (max 5000 characters)"}), 400

    if len(data.get("job_link", "") or "") > 500:
        return jsonify({"error": "Job link too long (max 500 characters)"}), 400

    status = data.get("status", "applied")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"Status must be one of {VALID_STATUSES}"}), 400

    deadline = None
    if data.get("deadline"):
        try:
            deadline = datetime.strptime(data["deadline"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Deadline must be in YYYY-MM-DD format"}), 400

    priority = data.get("priority", "medium")
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": f"Priority must be one of {VALID_PRIORITIES}"}), 400

    ats_score = data.get("ats_score")
    if ats_score is not None:
        try:
            ats_score = int(ats_score)
            if ats_score < 0 or ats_score > 100:
                return jsonify({"error": "ATS score must be between 0 and 100"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "ATS score must be an integer"}), 400

    job = Job(
        user_id=current_user.id,
        company=company,
        role=role,
        status=status,
        salary=data.get("salary"),
        recruiter=data.get("recruiter"),
        notes=data.get("notes"),
        deadline=deadline,
        job_link=data.get("job_link"),
        priority=priority,
        next_action=data.get("next_action"),
        resume_version=data.get("resume_version"),
        ats_score=ats_score,
        location=data.get("location"),
    )
    db.session.add(job)
    safe_commit()

    from app.core.integration import on_application_changed
    on_application_changed(current_user.id, job.id)

    return jsonify({"message": "Job created", "job": _serialize(job)}), 201


@jobs_bp.route("/<int:job_id>", methods=["GET"])
@login_required
def get_job(job_id):
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"job": _serialize(job)}), 200


@jobs_bp.route("/<int:job_id>", methods=["PUT"])
@login_required
def update_job(job_id):
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    data = request.get_json(silent=True) or {}

    if "company" in data and len(data["company"] or "") > 255:
        return jsonify({"error": "Company name too long (max 255 characters)"}), 400

    if "role" in data and len(data["role"] or "") > 255:
        return jsonify({"error": "Role too long (max 255 characters)"}), 400

    if "notes" in data and len(data["notes"] or "") > 5000:
        return jsonify({"error": "Notes too long (max 5000 characters)"}), 400

    if "job_link" in data and len(data["job_link"] or "") > 500:
        return jsonify({"error": "Job link too long (max 500 characters)"}), 400

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": f"Status must be one of {VALID_STATUSES}"}), 400
        job.status = data["status"]

    if "priority" in data:
        if data["priority"] not in VALID_PRIORITIES:
            return jsonify(
                {"error": f"Priority must be one of {VALID_PRIORITIES}"}
            ), 400
        job.priority = data["priority"]

    if "ats_score" in data:
        if data["ats_score"] is not None:
            try:
                val = int(data["ats_score"])
                if val < 0 or val > 100:
                    return jsonify(
                        {"error": "ATS score must be between 0 and 100"}
                    ), 400
                job.ats_score = val
            except (TypeError, ValueError):
                return jsonify({"error": "ATS score must be an integer"}), 400
        else:
            job.ats_score = None

    job.company = data.get("company", job.company)
    job.role = data.get("role", job.role)
    job.salary = data.get("salary", job.salary)
    job.recruiter = data.get("recruiter", job.recruiter)
    job.notes = data.get("notes", job.notes)
    job.job_link = data.get("job_link", job.job_link)
    job.next_action = data.get("next_action", job.next_action)
    job.resume_version = data.get("resume_version", job.resume_version)
    job.location = data.get("location", job.location)

    if "deadline" in data:
        if data["deadline"]:
            try:
                job.deadline = datetime.strptime(data["deadline"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Deadline must be in YYYY-MM-DD format"}), 400
        else:
            job.deadline = None

    safe_commit()

    from app.core.integration import on_application_changed
    on_application_changed(current_user.id, job.id)

    return jsonify({"message": "Job updated", "job": _serialize(job)}), 200


@jobs_bp.route("/<int:job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    db.session.delete(job)
    safe_commit()
    return jsonify({"message": "Job deleted"}), 200


@jobs_bp.route("/suggestions", methods=["GET"])
@login_required
def get_suggestions():
    jobs = (
        Job.query.filter_by(user_id=current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    has_resume = hasattr(current_user, "resume") and current_user.resume is not None

    suggestions = []

    if not has_resume:
        suggestions.append(
            {
                "id": "create-resume",
                "title": "Create your resume",
                "description": "An ATS-optimized resume is your first step to landing interviews.",
                "impact": "high",
                "category": "resume",
                "action": "Create Resume",
                "link": "/resume",
                "score_impact": "+15 ATS",
            }
        )

    if len(jobs) < 3:
        suggestions.append(
            {
                "id": "apply-more",
                "title": "Apply to more positions",
                "description": "Top performers apply to 10+ positions to maximize interview chances.",
                "impact": "high",
                "category": "applications",
                "action": "Add Application",
                "link": None,
                "score_impact": "+25% Interview Rate",
            }
        )
    else:
        applied = sum(1 for j in jobs if j.status == "applied")
        if applied > 0:
            suggestions.append(
                {
                    "id": "follow-up",
                    "title": "Follow up on applications",
                    "description": f"You have {applied} application{'s' if applied > 1 else ''} awaiting follow-up. Send a polite check-in email.",
                    "impact": "medium",
                    "category": "applications",
                    "action": "Review Applications",
                    "link": None,
                    "score_impact": "+10% Response Rate",
                }
            )

        oa_count = sum(1 for j in jobs if j.status == "oa")
        if oa_count > 0:
            suggestions.append(
                {
                    "id": "practice-oa",
                    "title": "Prepare for online assessments",
                    "description": f"Practice DSA and system design for your {oa_count} upcoming OA{'s' if oa_count > 1 else ''}.",
                    "impact": "high",
                    "category": "interview-prep",
                    "action": "Practice Now",
                    "link": "/coach",
                    "score_impact": "+20% OA Success",
                }
            )

        interview_count = sum(1 for j in jobs if j.status == "interview")
        if interview_count > 0:
            suggestions.append(
                {
                    "id": "interview-coach",
                    "title": "Practice interviews",
                    "description": f"You have {interview_count} upcoming interview{'s' if interview_count > 1 else ''}. Use the AI career coach to prepare.",
                    "impact": "high",
                    "category": "interview-prep",
                    "action": "Practice with Coach",
                    "link": "/coach",
                    "score_impact": "+30% Offer Rate",
                }
            )

    suggestions.append(
        {
            "id": "ats-score",
            "title": "Optimize your resume for ATS",
            "description": "Run an ATS check to ensure your resume passes automated filters.",
            "impact": "high",
            "category": "resume",
            "action": "Check ATS Score",
            "link": "/resume",
            "score_impact": "+6 ATS",
        }
    )

    suggestions.append(
        {
            "id": "linkedin-profile",
            "title": "Update your LinkedIn profile",
            "description": "Recruiters check LinkedIn — make sure your profile reflects your latest experience.",
            "impact": "medium",
            "category": "networking",
            "action": "Open LinkedIn",
            "link": None,
            "score_impact": "+15% Recruiter Outreach",
        }
    )

    return jsonify({"suggestions": suggestions}), 200
