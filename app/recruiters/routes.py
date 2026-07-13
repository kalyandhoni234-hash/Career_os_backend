import json
import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.auth.models import User
from app.users.models import Profile
from app.recruiters.models import (
    Recruiter,
    Company,
    JobPost,
    SavedCandidate,
    TalentPipeline,
    CandidateView,
    InterviewInvite,
    RecruiterNotification,
)
from app.resume.models import Resume
from sqlalchemy import or_

logger = logging.getLogger(__name__)

recruiters_bp = Blueprint("recruiters", __name__)


def recruiter_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "recruiter" and current_user.role != "admin":
            return jsonify({"error": "Recruiter access required"}), 403
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated


def _get_recruiter():
    return Recruiter.query.filter_by(user_id=current_user.id).first()


# ── Auth ────────────────────────────────────────────────────────────────────


@recruiters_bp.route("/ping")
def ping():
    return {"blueprint": "recruiters", "status": "alive"}


@recruiters_bp.route("/auth/signup", methods=["POST"])
@limiter.limit("5 per minute")
def recruiter_signup():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    company_name = data.get("company_name", "").strip()
    title = data.get("title", "").strip()

    if not email or not password or not company_name:
        return jsonify({"error": "Email, password, and company name are required"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email format"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    company = Company.query.filter_by(name=company_name).first()
    if not company:
        company = Company(name=company_name)
        db.session.add(company)
        db.session.flush()

    from app.extensions import bcrypt

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(email=email, password_hash=password_hash, role="recruiter")
    db.session.add(user)
    db.session.flush()

    recruiter = Recruiter(
        user_id=user.id, company_id=company.id, full_name=full_name, title=title
    )
    db.session.add(recruiter)
    db.session.commit()

    return jsonify({"message": "Recruiter account created", "user_id": user.id}), 201


@recruiters_bp.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def recruiter_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or user.role not in ("recruiter", "admin"):
        return jsonify({"error": "No recruiter account found with this email"}), 401
    if not user.password_hash:
        return jsonify({"error": "Use Google OAuth to login"}), 401

    from app.extensions import bcrypt

    if not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    from flask_login import login_user

    login_user(user)
    return jsonify(
        {"message": "Login successful", "user_id": user.id, "role": user.role}
    ), 200


@recruiters_bp.route("/auth/me", methods=["GET"])
@recruiter_required
def recruiter_me():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    company = Company.query.get(recruiter.company_id)
    return jsonify(
        {
            "id": recruiter.id,
            "user_id": current_user.id,
            "email": current_user.email,
            "full_name": recruiter.full_name,
            "title": recruiter.title,
            "phone": recruiter.phone,
            "linkedin": recruiter.linkedin,
            "department": recruiter.department,
            "company": {
                "id": company.id,
                "name": company.name,
                "website": company.website,
                "logo_url": company.logo_url,
                "industry": company.industry,
                "description": company.description,
                "company_size": company.company_size,
            }
            if company
            else None,
        }
    ), 200


# ── Company ────────────────────────────────────────────────────────────────


@recruiters_bp.route("/company", methods=["GET", "PUT"])
@recruiter_required
def company_crud():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    company = Company.query.get(recruiter.company_id)
    if not company:
        return jsonify({"error": "Company not found"}), 404

    if request.method == "GET":
        return jsonify(
            {
                "id": company.id,
                "name": company.name,
                "website": company.website,
                "logo_url": company.logo_url,
                "description": company.description,
                "industry": company.industry,
                "headquarters": company.headquarters,
                "company_size": company.company_size,
                "founded_year": company.founded_year,
                "linkedin_url": company.linkedin_url,
                "twitter_url": company.twitter_url,
                "culture_description": company.culture_description,
                "benefits_description": company.benefits_description,
            }
        ), 200

    data = request.get_json(silent=True) or {}
    for field in (
        "website",
        "logo_url",
        "description",
        "industry",
        "headquarters",
        "company_size",
        "founded_year",
        "linkedin_url",
        "twitter_url",
        "culture_description",
        "benefits_description",
    ):
        if field in data:
            setattr(company, field, data[field])
    db.session.commit()
    return jsonify({"message": "Company updated"}), 200


# ── Recruiter Profile ──────────────────────────────────────────────────────


@recruiters_bp.route("/profile", methods=["PUT"])
@recruiter_required
def update_recruiter_profile():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("full_name", "title", "phone", "linkedin", "department"):
        if field in data:
            setattr(recruiter, field, data[field])
    db.session.commit()
    return jsonify({"message": "Profile updated"}), 200


# ── Candidate Search ───────────────────────────────────────────────────────


@recruiters_bp.route("/candidates/search", methods=["GET"])
@recruiter_required
def search_candidates():
    q = request.args.get("q", "").strip().lower()
    skills = request.args.getlist("skills")
    colleges = request.args.getlist("colleges")
    degrees = request.args.getlist("degrees")
    branches = request.args.getlist("branches")
    locations = request.args.getlist("locations")
    remote = request.args.get("remote", type=bool)
    graduation_year = request.args.get("graduation_year", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    # Base query: only students
    query = (
        db.session.query(User, Profile, Resume)
        .outerjoin(Profile, User.id == Profile.user_id)
        .outerjoin(Resume, User.id == Resume.user_id)
        .filter(User.role == "student")
    )

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Resume.full_name.ilike(like),
                Resume.skills.astype(db.String).ilike(like),
                Profile.education.ilike(like),
                Profile.degree.ilike(like),
                Resume.github.ilike(like),
                Resume.linkedin.ilike(like),
                Resume.portfolio.ilike(like),
            )
        )

    if skills:
        for skill in skills:
            query = query.filter(Resume.skills.astype(db.String).ilike(f"%{skill}%"))

    if colleges:
        query = query.filter(Profile.education.in_(colleges))

    if degrees:
        query = query.filter(Profile.degree.in_(degrees))

    if branches:
        for branch in branches:
            query = query.filter(
                Resume.education.astype(db.String).ilike(f"%{branch}%")
            )

    if locations:
        query = query.filter(Resume.location.in_(locations))

    if remote is not None:
        query = query.filter(
            Profile.preferred_locations.astype(db.String).ilike("%remote%")
            if remote
            else ~Profile.preferred_locations.astype(db.String).ilike("%remote%")
        )

    if graduation_year:
        query = query.filter(Profile.graduation_year == graduation_year)

    total = query.count()
    results = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    candidates = []
    for user, profile, resume in results:
        candidate_data = _build_candidate_preview(user, profile, resume)
        candidates.append(candidate_data)

    return jsonify(
        {
            "candidates": candidates,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total else 0,
        }
    ), 200


def _build_candidate_preview(user, profile, resume):
    ats_score = None
    skills = []
    projects_count = 0
    certifications_count = 0
    full_name = None
    title = None
    location = None
    github = None
    linkedin = None
    portfolio = None

    if resume:
        ats_score = _get_ats_score(user.id)
        skills = resume.skills or []
        projects_count = len(resume.projects or [])
        certifications_count = len(resume.certificates or [])
        full_name = resume.full_name
        location = resume.location
        github = resume.github
        linkedin = resume.linkedin
        portfolio = resume.portfolio

    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": full_name or user.email.split("@")[0],
        "title": title,
        "skills": skills,
        "ats_score": ats_score,
        "projects_count": projects_count,
        "certifications_count": certifications_count,
        "location": location,
        "github": github,
        "linkedin": linkedin,
        "portfolio": portfolio,
        "education": profile.education if profile else None,
        "degree": profile.degree if profile else None,
        "graduation_year": profile.graduation_year if profile else None,
        "experience": profile.experience if profile else None,
        "has_resume": resume is not None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _get_ats_score(user_id):
    from app.resume.models import Resume

    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        return None
    from app.resume.ats import score_resume

    try:
        result = score_resume(resume, job_description="")
        return result.get("overall", None) if result else None
    except Exception:
        return None


# ── Candidate Detail ──────────────────────────────────────────────────────


@recruiters_bp.route("/candidates/<int:candidate_id>", methods=["GET"])
@recruiter_required
def candidate_detail(candidate_id):
    user = User.query.get(candidate_id)
    if not user or user.role != "student":
        return jsonify({"error": "Candidate not found"}), 404

    recruiter = _get_recruiter()
    if recruiter:
        view = CandidateView(
            recruiter_id=recruiter.id, candidate_id=candidate_id, source="profile_view"
        )
        db.session.add(view)
        db.session.commit()

    profile = Profile.query.filter_by(user_id=candidate_id).first()
    resume = Resume.query.filter_by(user_id=candidate_id).first()

    from app.career.models import CareerScoreSnapshot

    score_snap = (
        CareerScoreSnapshot.query.filter_by(user_id=candidate_id)
        .order_by(CareerScoreSnapshot.created_at.desc())
        .first()
    )

    data = {
        "user_id": user.id,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
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
            }
        )
    else:
        data.update(
            {
                k: None
                for k in (
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
                )
            }
        )

    if resume:
        data.update(
            {
                "resume": {
                    "id": resume.id,
                    "full_name": resume.full_name,
                    "email": resume.email,
                    "phone": resume.phone,
                    "location": resume.location,
                    "summary": resume.summary,
                    "title": resume.title,
                    "website": resume.website,
                    "linkedin": resume.linkedin,
                    "github": resume.github,
                    "portfolio": resume.portfolio,
                    "experience": resume.experience,
                    "education": resume.education,
                    "projects": resume.projects,
                    "skills": resume.skills,
                    "certificates": resume.certificates,
                    "achievements": resume.achievements,
                    "languages": resume.languages,
                    "target_job_description": resume.target_job_description,
                    "tone": resume.tone,
                    "created_at": resume.created_at.isoformat()
                    if resume.created_at
                    else None,
                    "updated_at": resume.updated_at.isoformat()
                    if resume.updated_at
                    else None,
                },
                "has_resume": True,
            }
        )

        ats_score = _get_ats_score(user.id)
        if ats_score:
            data["ats_score"] = ats_score
    else:
        data.update({"resume": None, "has_resume": False, "ats_score": None})

    if score_snap:
        data["career_score"] = {
            "overall": score_snap.overall_score,
            "resume": score_snap.resume_score,
            "projects": score_snap.projects_score,
            "skill_coverage": score_snap.skill_coverage,
            "breakdown": score_snap.breakdown,
        }
    else:
        data["career_score"] = None

    return jsonify({"candidate": data}), 200


# ── AI Candidate Summary ──────────────────────────────────────────────────


@recruiters_bp.route("/candidates/<int:candidate_id>/summary", methods=["GET"])
@recruiter_required
def candidate_ai_summary(candidate_id):
    user = User.query.get(candidate_id)
    if not user:
        return jsonify({"error": "Candidate not found"}), 404

    resume = Resume.query.filter_by(user_id=candidate_id).first()
    profile = Profile.query.filter_by(user_id=candidate_id).first()

    if not resume:
        return jsonify({"summary": None}), 200

    context_parts = []
    if resume.summary:
        context_parts.append(f"Professional Summary: {resume.summary}")
    if resume.skills:
        context_parts.append(f"Skills: {', '.join(resume.skills[:15])}")
    if resume.experience:
        exp_texts = []
        for exp in resume.experience[:3]:
            role = exp.get("role", "")
            company = exp.get("company", "")
            desc = exp.get("description", "")
            tech = exp.get("technologies", [])
            tech_str = f" [{', '.join(tech[:5])}]" if tech else ""
            exp_texts.append(f"{role} at {company}: {desc[:200]}{tech_str}")
        if exp_texts:
            context_parts.append("Experience:\n" + "\n".join(exp_texts))
    if resume.projects:
        proj_texts = [
            f"- {p.get('name', '')}: {p.get('description', '')[:100]}"
            for p in resume.projects[:5]
        ]
        context_parts.append("Projects:\n" + "\n".join(proj_texts))
    if resume.education:
        edu_texts = [
            f"{e.get('degree', '')} in {e.get('field', '')} at {e.get('school', '')}"
            for e in resume.education[:2]
        ]
        context_parts.append("Education:\n" + "\n".join(edu_texts))
    if profile and profile.preferred_roles:
        context_parts.append(f"Target Roles: {', '.join(profile.preferred_roles[:3])}")
    if resume.certificates:
        cert_names = [c.get("name", "") for c in resume.certificates[:3]]
        context_parts.append(f"Certifications: {', '.join(cert_names)}")

    context = "\n\n".join(context_parts)

    prompt = f"""Generate a concise, recruiter-friendly candidate summary (2-4 sentences) for a talent recruiter.

Candidate data:
{context}

Write in professional recruiter language. Highlight strengths, key skills, and what role they'd be a strong fit for. Be specific but concise."""

    from app.ai_service import generate_text

    try:
        summary = generate_text(prompt, model="gemini")
    except Exception as e:
        logger.warning("AI summary failed: %s", e)
        summary = None

    return jsonify({"summary": summary}), 200


# ── AI Match Score ────────────────────────────────────────────────────────


@recruiters_bp.route("/candidates/<int:candidate_id>/match", methods=["POST"])
@recruiter_required
def candidate_match_score(candidate_id):
    data = request.get_json(silent=True) or {}
    job_description = data.get("job_description", "")
    job_title = data.get("job_title", "")
    skills_required = data.get("skills_required", [])

    user = User.query.get(candidate_id)
    if not user:
        return jsonify({"error": "Candidate not found"}), 404

    resume = Resume.query.filter_by(user_id=candidate_id).first()
    if not resume:
        return jsonify({"match": None, "reason": "Candidate has no resume"}), 200

    match_prompt = f"""Analyze this candidate for the role "{job_title or "the position"}" and calculate a match score.

Job Requirements:
- Skills needed: {", ".join(skills_required) if skills_required else "Not specified"}
- Description: {job_description[:500] if job_description else "Not provided"}

Candidate Profile:
- Skills: {", ".join(resume.skills or [])}
- Experience: {json.dumps(resume.experience or [], indent=2)[:500]}
- Projects: {json.dumps(resume.projects or [], indent=2)[:500]}
- Summary: {resume.summary or "N/A"}

Return valid JSON only with this structure:
{{"match_score": <0-100 integer>, "strengths": ["strength1", "strength2", ...], "gaps": ["gap1", "gap2", ...], "reason": "<1-2 sentence explanation>"}}"""

    import json as json_lib
    from app.ai_service import generate_text

    try:
        raw = generate_text(match_prompt, model="gemini")
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        result = json_lib.loads(cleaned)
        return jsonify({"match": result}), 200
    except Exception as e:
        logger.warning("AI match failed: %s", e)
        return jsonify({"match": None, "reason": "Failed to compute match score"}), 200


# ── Saved Candidates / Pipelines ──────────────────────────────────────────


@recruiters_bp.route("/candidates/saved", methods=["GET"])
@recruiter_required
def list_saved_candidates():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    saved = SavedCandidate.query.filter_by(recruiter_id=recruiter.id).all()
    results = []
    for s in saved:
        candidate = User.query.get(s.candidate_id)
        profile = Profile.query.filter_by(user_id=s.candidate_id).first()
        resume = Resume.query.filter_by(user_id=s.candidate_id).first()
        pipeline_name = None
        pipeline_color = None
        if s.pipeline:
            pipeline_name = s.pipeline.name
            pipeline_color = s.pipeline.color

        preview = _build_candidate_preview(candidate, profile, resume)
        preview.update(
            {
                "saved_id": s.id,
                "notes": s.notes,
                "rating": s.rating,
                "status": s.status,
                "pipeline_name": pipeline_name,
                "pipeline_color": pipeline_color,
                "saved_at": s.created_at.isoformat() if s.created_at else None,
            }
        )
        results.append(preview)

    return jsonify({"saved_candidates": results}), 200


@recruiters_bp.route("/candidates/saved", methods=["POST"])
@recruiter_required
def save_candidate():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    data = request.get_json(silent=True) or {}
    candidate_id = data.get("candidate_id")
    pipeline_id = data.get("pipeline_id")
    notes = data.get("notes")

    if not candidate_id:
        return jsonify({"error": "candidate_id is required"}), 400

    existing = SavedCandidate.query.filter_by(
        recruiter_id=recruiter.id, candidate_id=candidate_id
    ).first()
    if existing:
        return jsonify({"error": "Candidate already saved"}), 409

    saved = SavedCandidate(
        recruiter_id=recruiter.id,
        candidate_id=candidate_id,
        pipeline_id=pipeline_id,
        notes=notes,
    )
    db.session.add(saved)
    db.session.commit()

    return jsonify({"message": "Candidate saved", "saved_id": saved.id}), 201


@recruiters_bp.route("/candidates/saved/<int:saved_id>", methods=["DELETE"])
@recruiter_required
def unsave_candidate(saved_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    saved = SavedCandidate.query.filter_by(
        id=saved_id, recruiter_id=recruiter.id
    ).first()
    if not saved:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(saved)
    db.session.commit()
    return jsonify({"message": "Candidate removed"}), 200


@recruiters_bp.route("/candidates/saved/<int:saved_id>", methods=["PUT"])
@recruiter_required
def update_saved_candidate(saved_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    saved = SavedCandidate.query.filter_by(
        id=saved_id, recruiter_id=recruiter.id
    ).first()
    if not saved:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("notes", "rating", "status", "pipeline_id"):
        if field in data:
            setattr(saved, field, data[field])
    db.session.commit()
    return jsonify({"message": "Updated"}), 200


# ── Talent Pipelines ──────────────────────────────────────────────────────


@recruiters_bp.route("/pipelines", methods=["GET"])
@recruiter_required
def list_pipelines():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    pipelines = TalentPipeline.query.filter_by(recruiter_id=recruiter.id).all()
    results = []
    for p in pipelines:
        count = SavedCandidate.query.filter_by(pipeline_id=p.id).count()
        results.append(
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "color": p.color,
                "candidate_count": count,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )
    return jsonify({"pipelines": results}), 200


@recruiters_bp.route("/pipelines", methods=["POST"])
@recruiter_required
def create_pipeline():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Pipeline name is required"}), 400

    pipeline = TalentPipeline(
        recruiter_id=recruiter.id,
        name=name,
        description=data.get("description"),
        color=data.get("color"),
    )
    db.session.add(pipeline)
    db.session.commit()

    return jsonify(
        {
            "message": "Pipeline created",
            "pipeline": {
                "id": pipeline.id,
                "name": pipeline.name,
                "description": pipeline.description,
                "color": pipeline.color,
                "candidate_count": 0,
                "created_at": pipeline.created_at.isoformat()
                if pipeline.created_at
                else None,
            },
        }
    ), 201


@recruiters_bp.route("/pipelines/<int:pipeline_id>", methods=["PUT", "DELETE"])
@recruiter_required
def pipeline_crud(pipeline_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    pipeline = TalentPipeline.query.filter_by(
        id=pipeline_id, recruiter_id=recruiter.id
    ).first()
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    if request.method == "DELETE":
        db.session.delete(pipeline)
        db.session.commit()
        return jsonify({"message": "Pipeline deleted"}), 200

    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "color"):
        if field in data:
            setattr(pipeline, field, data[field])
    db.session.commit()
    return jsonify({"message": "Pipeline updated"}), 200


# ── Job Posts ────────────────────────────────────────────────────────────


@recruiters_bp.route("/jobs", methods=["GET"])
@recruiter_required
def list_job_posts():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    jobs = (
        JobPost.query.filter_by(recruiter_id=recruiter.id)
        .order_by(JobPost.created_at.desc())
        .all()
    )
    results = []
    for job in jobs:
        candidate_count = InterviewInvite.query.filter_by(job_post_id=job.id).count()
        results.append(
            {
                "id": job.id,
                "title": job.title,
                "location": job.location,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "employment_type": job.employment_type,
                "skills_required": job.skills_required,
                "status": job.status,
                "is_remote": job.is_remote,
                "candidate_count": candidate_count,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            }
        )
    return jsonify({"jobs": results}), 200


@recruiters_bp.route("/jobs/<int:job_id>", methods=["GET"])
@recruiter_required
def get_job_post(job_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    job = JobPost.query.filter_by(id=job_id).first()
    if not job:
        return jsonify({"error": "Job post not found"}), 404

    invites = InterviewInvite.query.filter_by(job_post_id=job.id).count()
    return jsonify(
        {
            "job": {
                "id": job.id,
                "title": job.title,
                "description": job.description,
                "location": job.location,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "salary_currency": job.salary_currency,
                "experience_required": job.experience_required,
                "experience_max": job.experience_max,
                "employment_type": job.employment_type,
                "skills_required": job.skills_required,
                "benefits": job.benefits,
                "application_deadline": job.application_deadline.isoformat()
                if job.application_deadline
                else None,
                "status": job.status,
                "is_remote": job.is_remote,
                "candidate_count": invites,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            }
        }
    ), 200


@recruiters_bp.route("/jobs", methods=["POST"])
@recruiter_required
def create_job_post():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    if not title or not description:
        return jsonify({"error": "Title and description are required"}), 400

    job = JobPost(
        recruiter_id=recruiter.id,
        company_id=recruiter.company_id,
        title=title,
        description=description,
        location=data.get("location"),
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        salary_currency=data.get("salary_currency", "USD"),
        experience_required=data.get("experience_required"),
        experience_max=data.get("experience_max"),
        employment_type=data.get("employment_type"),
        skills_required=data.get("skills_required"),
        benefits=data.get("benefits"),
        application_deadline=datetime.fromisoformat(data["application_deadline"]).date()
        if data.get("application_deadline")
        else None,
        is_remote=data.get("is_remote", False),
        status=data.get("status", "active"),
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({"message": "Job post created", "job_id": job.id}), 201


@recruiters_bp.route("/jobs/<int:job_id>", methods=["PUT"])
@recruiter_required
def update_job_post(job_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    job = JobPost.query.filter_by(id=job_id, recruiter_id=recruiter.id).first()
    if not job:
        return jsonify({"error": "Job post not found"}), 404

    data = request.get_json(silent=True) or {}
    text_fields = (
        "title",
        "description",
        "location",
        "experience_required",
        "experience_max",
        "employment_type",
        "salary_currency",
        "status",
    )
    for field in text_fields:
        if field in data:
            setattr(job, field, data[field])
    for field in ("salary_min", "salary_max"):
        if field in data:
            setattr(job, field, data[field])
    if "is_remote" in data:
        job.is_remote = data["is_remote"]
    if "skills_required" in data:
        job.skills_required = data["skills_required"]
    if "benefits" in data:
        job.benefits = data["benefits"]
    if data.get("application_deadline"):
        job.application_deadline = datetime.fromisoformat(
            data["application_deadline"]
        ).date()
    db.session.commit()

    return jsonify({"message": "Job post updated"}), 200


@recruiters_bp.route("/jobs/<int:job_id>", methods=["DELETE"])
@recruiter_required
def delete_job_post(job_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    job = JobPost.query.filter_by(id=job_id, recruiter_id=recruiter.id).first()
    if not job:
        return jsonify({"error": "Job post not found"}), 404

    db.session.delete(job)
    db.session.commit()
    return jsonify({"message": "Job post deleted"}), 200


# ── Interview Invites ───────────────────────────────────────────────────


@recruiters_bp.route("/invites", methods=["GET"])
@recruiter_required
def list_invites():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    invites = (
        InterviewInvite.query.filter_by(recruiter_id=recruiter.id)
        .order_by(InterviewInvite.created_at.desc())
        .all()
    )
    results = []
    for inv in invites:
        candidate = User.query.get(inv.candidate_id)
        candidate_name = candidate.email.split("@")[0] if candidate else "Unknown"
        job_title = None
        if inv.job_post:
            job_title = inv.job_post.title
        results.append(
            {
                "id": inv.id,
                "candidate_id": inv.candidate_id,
                "candidate_name": candidate_name,
                "job_post_id": inv.job_post_id,
                "job_title": job_title,
                "message": inv.message,
                "interview_type": inv.interview_type,
                "scheduled_date": inv.scheduled_date.isoformat()
                if inv.scheduled_date
                else None,
                "duration_minutes": inv.duration_minutes,
                "location": inv.location,
                "status": inv.status,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
        )
    return jsonify({"invites": results}), 200


@recruiters_bp.route("/invites", methods=["POST"])
@recruiter_required
def create_invite():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    data = request.get_json(silent=True) or {}
    candidate_id = data.get("candidate_id")
    if not candidate_id:
        return jsonify({"error": "candidate_id is required"}), 400

    invite = InterviewInvite(
        recruiter_id=recruiter.id,
        candidate_id=candidate_id,
        job_post_id=data.get("job_post_id"),
        message=data.get("message"),
        interview_type=data.get("interview_type", "phone"),
        scheduled_date=datetime.fromisoformat(data["scheduled_date"])
        if data.get("scheduled_date")
        else None,
        duration_minutes=data.get("duration_minutes", 60),
        location=data.get("location"),
    )
    db.session.add(invite)

    notification = RecruiterNotification(
        recruiter_id=recruiter.id,
        type="invite_sent",
        title="Interview invite sent",
        message=f"Invited candidate for {invite.interview_type} interview",
        data={"invite_id": invite.id, "candidate_id": candidate_id},
    )
    db.session.add(notification)
    db.session.commit()

    return jsonify({"message": "Invite sent", "invite_id": invite.id}), 201


@recruiters_bp.route("/invites/<int:invite_id>", methods=["PUT"])
@recruiter_required
def update_invite(invite_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    invite = InterviewInvite.query.filter_by(
        id=invite_id, recruiter_id=recruiter.id
    ).first()
    if not invite:
        return jsonify({"error": "Invite not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in (
        "message",
        "interview_type",
        "location",
        "status",
        "duration_minutes",
    ):
        if field in data:
            setattr(invite, field, data[field])
    if data.get("scheduled_date"):
        invite.scheduled_date = datetime.fromisoformat(data["scheduled_date"])
    db.session.commit()
    return jsonify({"message": "Invite updated"}), 200


# ── Notifications ────────────────────────────────────────────────────────


@recruiters_bp.route("/notifications", methods=["GET"])
@recruiter_required
def list_notifications():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    unread_only = request.args.get("unread_only", type=bool)
    query = RecruiterNotification.query.filter_by(recruiter_id=recruiter.id)
    if unread_only:
        query = query.filter_by(is_read=False)
    notifications = (
        query.order_by(RecruiterNotification.created_at.desc()).limit(50).all()
    )

    results = []
    for n in notifications:
        results.append(
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "data": n.data,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
        )
    return jsonify({"notifications": results}), 200


@recruiters_bp.route("/notifications/read", methods=["POST"])
@recruiter_required
def mark_notifications_read():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    data = request.get_json(silent=True) or {}
    notification_ids = data.get("notification_ids", [])
    if notification_ids:
        RecruiterNotification.query.filter(
            RecruiterNotification.id.in_(notification_ids),
            RecruiterNotification.recruiter_id == recruiter.id,
        ).update({"is_read": True}, synchronize_session=False)
    else:
        RecruiterNotification.query.filter_by(
            recruiter_id=recruiter.id, is_read=False
        ).update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "Notifications marked read"}), 200


# ── Dashboard ────────────────────────────────────────────────────────────


@recruiters_bp.route("/dashboard", methods=["GET"])
@recruiter_required
def recruiter_dashboard():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    total_candidates = User.query.filter_by(role="student").count()

    active_jobs = JobPost.query.filter_by(
        recruiter_id=recruiter.id, status="active"
    ).count()

    saved_count = SavedCandidate.query.filter_by(recruiter_id=recruiter.id).count()

    recent_applications = (
        SavedCandidate.query.filter_by(recruiter_id=recruiter.id)
        .order_by(SavedCandidate.created_at.desc())
        .limit(10)
        .all()
    )

    invites = InterviewInvite.query.filter_by(recruiter_id=recruiter.id).all()
    pending_invites = len([i for i in invites if i.status == "pending"])
    total_invites = len(invites)

    total_views = CandidateView.query.filter_by(recruiter_id=recruiter.id).count()

    recent_activity = []
    for s in recent_applications:
        candidate = User.query.get(s.candidate_id)
        name = candidate.email.split("@")[0] if candidate else "Unknown"
        recent_activity.append(
            {
                "type": "saved",
                "description": f"Saved {name} to pipeline",
                "timestamp": s.created_at.isoformat() if s.created_at else None,
            }
        )

    for inv in (
        InterviewInvite.query.filter_by(recruiter_id=recruiter.id)
        .order_by(InterviewInvite.created_at.desc())
        .limit(5)
        .all()
    ):
        candidate = User.query.get(inv.candidate_id)
        name = candidate.email.split("@")[0] if candidate else "Unknown"
        recent_activity.append(
            {
                "type": "invite",
                "description": f"Invited {name} for {inv.interview_type} interview",
                "timestamp": inv.created_at.isoformat() if inv.created_at else None,
            }
        )

    recent_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    recent_activity = recent_activity[:10]

    total_jobs = JobPost.query.filter_by(recruiter_id=recruiter.id).count()

    return jsonify(
        {
            "total_candidates": total_candidates,
            "active_jobs": active_jobs,
            "saved_candidates": saved_count,
            "total_jobs": total_jobs,
            "pending_invites": pending_invites,
            "total_invites": total_invites,
            "total_views": total_views,
            "recent_activity": recent_activity,
        }
    ), 200


# ── Analytics ────────────────────────────────────────────────────────────


@recruiters_bp.route("/analytics", methods=["GET"])
@recruiter_required
def recruiter_analytics():
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    invites = InterviewInvite.query.filter_by(recruiter_id=recruiter.id).all()
    total_sent = len(invites)
    accepted = len([i for i in invites if i.status == "accepted"])
    rejected = len([i for i in invites if i.status == "rejected"])
    pending = len([i for i in invites if i.status == "pending"])

    interview_rate = round((total_sent / total_sent * 100), 1) if total_sent > 0 else 0
    accepted_rate = round((accepted / total_sent * 100), 1) if total_sent > 0 else 0

    all_students = User.query.filter_by(role="student").count()

    ats_scores = []
    for user in User.query.filter_by(role="student").limit(100):
        score = _get_ats_score(user.id)
        if score:
            ats_scores.append(score)
    avg_ats = round(sum(ats_scores) / len(ats_scores), 1) if ats_scores else 0

    top_colleges = (
        db.session.query(Profile.education, db.func.count(Profile.id).label("count"))
        .filter(Profile.education.isnot(None))
        .group_by(Profile.education)
        .order_by(db.desc("count"))
        .limit(10)
        .all()
    )

    top_skills = {}
    for user in User.query.filter_by(role="student").limit(200):
        resume = Resume.query.filter_by(user_id=user.id).first()
        if resume and resume.skills:
            for skill in resume.skills:
                top_skills[skill] = top_skills.get(skill, 0) + 1
    top_skills_sorted = sorted(top_skills.items(), key=lambda x: x[1], reverse=True)[
        :20
    ]

    return jsonify(
        {
            "total_candidates_viewed": total_sent,
            "invites_sent": total_sent,
            "invites_accepted": accepted,
            "invites_pending": pending,
            "invites_rejected": rejected,
            "interview_rate": interview_rate,
            "acceptance_rate": accepted_rate,
            "total_students": all_students,
            "average_ats_score": avg_ats,
            "top_colleges": [{"name": c[0], "count": c[1]} for c in top_colleges],
            "top_skills": [
                {"name": s[0], "count": s[1]} for s in top_skills_sorted[:10]
            ],
        }
    ), 200


# ── Candidate Compare ────────────────────────────────────────────────────


@recruiters_bp.route("/candidates/compare", methods=["POST"])
@recruiter_required
def compare_candidates():
    data = request.get_json(silent=True) or {}
    candidate_ids = data.get("candidate_ids", [])
    if not candidate_ids or len(candidate_ids) < 2:
        return jsonify({"error": "Provide at least 2 candidate_ids"}), 400
    if len(candidate_ids) > 5:
        return jsonify({"error": "Compare up to 5 candidates at once"}), 400

    results = []
    for cid in candidate_ids:
        user = User.query.get(cid)
        if not user or user.role != "student":
            continue
        profile = Profile.query.filter_by(user_id=cid).first()
        resume = Resume.query.filter_by(user_id=cid).first()
        preview = _build_candidate_preview(user, profile, resume)

        ats = _get_ats_score(cid)
        career_score = None
        from app.career.models import CareerScoreSnapshot

        snap = (
            CareerScoreSnapshot.query.filter_by(user_id=cid)
            .order_by(CareerScoreSnapshot.created_at.desc())
            .first()
        )
        if snap:
            career_score = snap.overall_score

        preview.update(
            {
                "ats_score": ats,
                "career_score": career_score,
            }
        )
        results.append(preview)

    return jsonify({"candidates": results}), 200


# ── Contact Candidate ────────────────────────────────────────────────────


@recruiters_bp.route("/candidates/<int:candidate_id>/contact", methods=["POST"])
@recruiter_required
def contact_candidate(candidate_id):
    recruiter = _get_recruiter()
    if not recruiter:
        return jsonify({"error": "Recruiter profile not found"}), 404

    data = request.get_json(silent=True) or {}
    action = data.get("action", "")

    if action == "request_resume":
        notification = RecruiterNotification(
            recruiter_id=recruiter.id,
            type="resume_request",
            title="Resume requested",
            message=f"You requested a resume from candidate {candidate_id}",
            data={"candidate_id": candidate_id},
        )
        db.session.add(notification)
        db.session.commit()
        return jsonify({"message": "Resume request sent"}), 200

    if action == "save":
        existing = SavedCandidate.query.filter_by(
            recruiter_id=recruiter.id, candidate_id=candidate_id
        ).first()
        if existing:
            return jsonify({"error": "Already saved"}), 409
        saved = SavedCandidate(
            recruiter_id=recruiter.id, candidate_id=candidate_id, status="contacted"
        )
        db.session.add(saved)
        db.session.commit()
        return jsonify({"message": "Candidate saved", "saved_id": saved.id}), 201

    if action == "reject":
        saved = SavedCandidate.query.filter_by(
            recruiter_id=recruiter.id, candidate_id=candidate_id
        ).first()
        if saved:
            saved.status = "rejected"
            db.session.commit()
        return jsonify({"message": "Candidate rejected"}), 200

    return jsonify({"error": "Invalid action"}), 400


# ── AI-Candidate Matching (for a job) ────────────────────────────────────


@recruiters_bp.route("/jobs/<int:job_id>/match", methods=["GET"])
@recruiter_required
def match_candidates_to_job(job_id):
    job = JobPost.query.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    limit = request.args.get("limit", 20, type=int)
    skills_required = set(s.lower() for s in (job.skills_required or []))

    students = User.query.filter_by(role="student").all()
    scored = []

    for user in students:
        resume = Resume.query.filter_by(user_id=user.id).first()
        if not resume or not resume.skills:
            continue

        candidate_skills = set(s.lower() for s in (resume.skills or []))
        if skills_required:
            overlap = len(candidate_skills & skills_required)
            total = len(skills_required)
            skill_match = round((overlap / total) * 100) if total > 0 else 0
        else:
            skill_match = 0

        ats = _get_ats_score(user.id) or 0

        profile = Profile.query.filter_by(user_id=user.id).first()
        match_score = min(100, int(skill_match * 0.6 + ats * 0.4))

        scored.append(
            {
                "user_id": user.id,
                "full_name": resume.full_name or user.email.split("@")[0],
                "skills": resume.skills or [],
                "ats_score": ats,
                "skill_match": skill_match,
                "match_score": match_score,
                "has_resume": True,
                "education": profile.education if profile else None,
                "degree": profile.degree if profile else None,
                "location": resume.location,
            }
        )

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    top = scored[:limit]

    return jsonify({"matches": top, "total": len(top)}), 200


# ── Bulk lookup helpers ─────────────────────────────────────────────────


@recruiters_bp.route("/candidates/bulk", methods=["POST"])
@recruiter_required
def bulk_candidate_lookup():
    data = request.get_json(silent=True) or {}
    candidate_ids = data.get("candidate_ids", [])
    if not candidate_ids:
        return jsonify({"error": "candidate_ids required"}), 400

    results = []
    for cid in candidate_ids:
        user = User.query.get(cid)
        if not user or user.role != "student":
            continue
        profile = Profile.query.filter_by(user_id=cid).first()
        resume = Resume.query.filter_by(user_id=cid).first()
        results.append(_build_candidate_preview(user, profile, resume))

    return jsonify({"candidates": results}), 200
