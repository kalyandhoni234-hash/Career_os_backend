from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.jobs.models import Job

jobs_bp = Blueprint("jobs", __name__)

VALID_STATUSES = ["applied", "oa", "interview", "offer", "rejected"]

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
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }

@jobs_bp.route("/ping")
def ping():
    return {"blueprint": "jobs", "status": "alive"}

@jobs_bp.route("", methods=["GET"])
@login_required
def list_jobs():
    jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).all()
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
    )
    db.session.add(job)
    db.session.commit()

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

    job.company = data.get("company", job.company)
    job.role = data.get("role", job.role)
    job.salary = data.get("salary", job.salary)
    job.recruiter = data.get("recruiter", job.recruiter)
    job.notes = data.get("notes", job.notes)
    job.job_link = data.get("job_link", job.job_link)

    if "deadline" in data:
        if data["deadline"]:
            try:
                job.deadline = datetime.strptime(data["deadline"], "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "Deadline must be in YYYY-MM-DD format"}), 400
        else:
            job.deadline = None

    db.session.commit()
    return jsonify({"message": "Job updated", "job": _serialize(job)}), 200

@jobs_bp.route("/<int:job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return jsonify({"error": "Job not found"}), 404

    db.session.delete(job)
    db.session.commit()
    return jsonify({"message": "Job deleted"}), 200
