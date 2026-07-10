import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.opportunities.models import (
    Opportunity,
    SavedOpportunity,
)
from app.opportunities.services import (
    search_opportunities,
    get_opportunity_detail,
    create_opportunity,
    update_opportunity,
    seed_sample_opportunities,
    get_company_insights,
    search_companies,
    estimate_salary,
    get_market_trends,
    calculate_match_score,
    analyze_opportunity_skill_gaps,
    generate_optimized_resume,
    generate_cover_letter,
    generate_email,
    generate_linkedin_message,
    generate_interview_questions,
)

logger = logging.getLogger(__name__)

opportunities_bp = Blueprint("opportunities", __name__)


@opportunities_bp.route("/ping")
def ping():
    return {"blueprint": "opportunities", "status": "alive"}


@opportunities_bp.route("/seed", methods=["POST"])
def seed():
    seed_sample_opportunities()
    return jsonify({"message": "Sample opportunities seeded"}), 200


# ── Search & List ──────────────────────────────────────────


@opportunities_bp.route("", methods=["GET"])
def list_opportunities():
    kwargs = {
        "query": request.args.get("q"),
        "location": request.args.get("location"),
        "remote_type": request.args.get("remote_type"),
        "employment_type": request.args.get("employment_type"),
        "company": request.args.get("company"),
        "sort_by": request.args.get("sort_by", "posted_at"),
        "sort_order": request.args.get("sort_order", "desc"),
        "page": int(request.args.get("page", 1)),
        "per_page": min(int(request.args.get("per_page", 20)), 100),
    }

    for key in ("salary_min", "salary_max", "experience_min", "experience_max"):
        val = request.args.get(key)
        if val:
            kwargs[key] = int(val)

    ts = request.args.get("tech_stack")
    if ts:
        kwargs["tech_stack"] = [t.strip() for t in ts.split(",")]

    min_match = request.args.get("min_match_score")
    if min_match and current_user.is_authenticated:
        kwargs["min_match_score"] = int(min_match)
        kwargs["user_id"] = current_user.id

    result = search_opportunities(**kwargs)
    return jsonify(result), 200


@opportunities_bp.route("/<int:opportunity_id>", methods=["GET"])
def get_opportunity(opportunity_id):
    detail = get_opportunity_detail(opportunity_id)
    if not detail:
        return jsonify({"error": "Opportunity not found"}), 404

    result = {"opportunity": detail}

    if current_user.is_authenticated:
        saved = SavedOpportunity.query.filter_by(
            user_id=current_user.id, opportunity_id=opportunity_id
        ).first()
        if saved:
            result["saved"] = {
                "id": saved.id,
                "list_type": saved.list_type,
                "notes": saved.notes,
                "tags": saved.tags,
            }

    return jsonify(result), 200


@opportunities_bp.route("", methods=["POST"])
@login_required
def create_opportunity_endpoint():
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("company_name"):
        return jsonify({"error": "title and company_name are required"}), 400
    opp = create_opportunity(data)
    return jsonify({"opportunity": opp}), 201


@opportunities_bp.route("/<int:opportunity_id>", methods=["PUT"])
@login_required
def update_opportunity_endpoint(opportunity_id):
    data = request.get_json(silent=True) or {}
    opp = get_opportunity_detail(opportunity_id)
    if not opp:
        return jsonify({"error": "Opportunity not found"}), 404
    updated = update_opportunity(opportunity_id, data)
    return jsonify({"opportunity": updated}), 200


# ── Saved Jobs ─────────────────────────────────────────────


@opportunities_bp.route("/saved", methods=["GET"])
@login_required
def list_saved_opportunities():
    list_type = request.args.get("list_type")
    include_scores = request.args.get("include_scores", "false").lower() == "true"
    q = SavedOpportunity.query.filter_by(user_id=current_user.id)
    if list_type:
        q = q.filter_by(list_type=list_type)
    saved = q.order_by(SavedOpportunity.created_at.desc()).all()

    result = []
    for s in saved:
        opp = Opportunity.query.get(s.opportunity_id)
        if not opp:
            continue
        item = {
            "saved_id": s.id,
            "list_type": s.list_type,
            "tags": s.tags or [],
            "notes": s.notes,
            "applied_at": s.applied_at.isoformat() if s.applied_at else None,
            "application_status": s.application_status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "opportunity": {
                "id": opp.id,
                "title": opp.title,
                "company_name": opp.company_name,
                "company_logo": opp.company_logo,
                "location": opp.location,
                "remote_type": opp.remote_type,
                "salary_min": opp.salary_min,
                "salary_max": opp.salary_max,
                "currency": opp.currency,
                "employment_type": opp.employment_type,
                "tech_stack": opp.tech_stack or [],
            },
        }
        if include_scores:
            score = calculate_match_score(current_user.id, s.opportunity_id)
            item["match_score"] = {
                "overall_score": score.get("overall_score", 0),
                "ats_match": score.get("ats_match", 0),
                "skill_match": score.get("skill_match", 0),
                "experience_match": score.get("experience_match", 0),
            }
        result.append(item)

    return jsonify({"saved": result}), 200


@opportunities_bp.route("/<int:opportunity_id>/save", methods=["POST"])
@login_required
def save_opportunity(opportunity_id):
    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return jsonify({"error": "Opportunity not found"}), 404

    existing = SavedOpportunity.query.filter_by(
        user_id=current_user.id, opportunity_id=opportunity_id
    ).first()
    if existing:
        data = request.get_json(silent=True) or {}
        existing.list_type = data.get("list_type", existing.list_type)
        return jsonify({"message": "Already saved", "saved_id": existing.id}), 200

    data = request.get_json(silent=True) or {}
    saved = SavedOpportunity(
        user_id=current_user.id,
        opportunity_id=opportunity_id,
        list_type=data.get("list_type", "saved"),
        tags=data.get("tags", []),
        notes=data.get("notes"),
    )
    db.session.add(saved)
    db.session.commit()

    return jsonify({"message": "Opportunity saved", "saved_id": saved.id}), 201


@opportunities_bp.route("/<int:opportunity_id>/save", methods=["PUT"])
@login_required
def update_saved_opportunity(opportunity_id):
    saved = SavedOpportunity.query.filter_by(
        user_id=current_user.id, opportunity_id=opportunity_id
    ).first()
    if not saved:
        return jsonify({"error": "Not saved"}), 404

    data = request.get_json(silent=True) or {}
    for field in ("list_type", "tags", "notes", "application_status"):
        if field in data:
            setattr(saved, field, data[field])
    if data.get("applied"):
        saved.applied_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({"message": "Updated"}), 200


@opportunities_bp.route("/<int:opportunity_id>/save", methods=["DELETE"])
@login_required
def unsave_opportunity(opportunity_id):
    saved = SavedOpportunity.query.filter_by(
        user_id=current_user.id, opportunity_id=opportunity_id
    ).first()
    if not saved:
        return jsonify({"error": "Not saved"}), 404
    db.session.delete(saved)
    db.session.commit()
    return jsonify({"message": "Removed"}), 200


# ── Match Scores ───────────────────────────────────────────


@opportunities_bp.route("/<int:opportunity_id>/match", methods=["GET"])
@login_required
def get_match_score(opportunity_id):
    force = request.args.get("force", "false").lower() == "true"
    score = calculate_match_score(current_user.id, opportunity_id, force=force)
    return jsonify({"match_score": score}), 200


# ── Skill Gaps ─────────────────────────────────────────────


@opportunities_bp.route("/<int:opportunity_id>/skill-gaps", methods=["GET"])
@login_required
def get_skill_gaps(opportunity_id):
    force = request.args.get("force", "false").lower() == "true"
    gaps = analyze_opportunity_skill_gaps(current_user.id, opportunity_id, force=force)
    return jsonify({"skill_gaps": gaps}), 200


# ── Resume Optimization ────────────────────────────────────


@opportunities_bp.route("/<int:opportunity_id>/optimize-resume", methods=["POST"])
@login_required
def optimize_resume_for_opportunity(opportunity_id):
    result = generate_optimized_resume(current_user.id, opportunity_id)
    return jsonify({"optimization": result}), 200


@opportunities_bp.route("/<int:opportunity_id>/cover-letter", methods=["POST"])
@login_required
def generate_cover_letter_endpoint(opportunity_id):
    data = request.get_json(silent=True) or {}
    tone = data.get("tone", "professional")
    result = generate_cover_letter(current_user.id, opportunity_id, tone=tone)
    return jsonify({"cover_letter": result}), 200


@opportunities_bp.route("/<int:opportunity_id>/email", methods=["POST"])
@login_required
def generate_email_endpoint(opportunity_id):
    data = request.get_json(silent=True) or {}
    email_type = data.get("email_type", "application")
    result = generate_email(current_user.id, opportunity_id, email_type=email_type)
    return jsonify({"email": result}), 200


@opportunities_bp.route("/<int:opportunity_id>/linkedin-message", methods=["POST"])
@login_required
def generate_linkedin_message_endpoint(opportunity_id):
    data = request.get_json(silent=True) or {}
    msg_type = data.get("message_type", "connection")
    result = generate_linkedin_message(
        current_user.id, opportunity_id, message_type=msg_type
    )
    return jsonify({"message": result}), 200


@opportunities_bp.route("/<int:opportunity_id>/interview-prep", methods=["GET"])
@login_required
def get_interview_prep(opportunity_id):
    result = generate_interview_questions(current_user.id, opportunity_id)
    return jsonify({"interview_pack": result}), 200


# ── Company Intelligence ───────────────────────────────────


@opportunities_bp.route("/companies", methods=["GET"])
def list_companies():
    query = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    result = search_companies(query, page=page, per_page=per_page)
    return jsonify(result), 200


@opportunities_bp.route("/companies/<path:company_name>", methods=["GET"])
def get_company(company_name):
    insights = get_company_insights(company_name)
    if not insights:
        return jsonify({"error": "Company not found"}), 404
    return jsonify({"company": insights}), 200


# ── Salary Intelligence ────────────────────────────────────


@opportunities_bp.route("/salary", methods=["GET"])
def salary_estimate():
    role = request.args.get("role", "")
    location = request.args.get("location")
    experience_level = request.args.get("experience_level")
    skills_param = request.args.get("skills")
    skills = [s.strip() for s in skills_param.split(",")] if skills_param else None

    if not role:
        return jsonify({"error": "role is required"}), 400

    result = estimate_salary(
        role, location=location, experience_level=experience_level, skills=skills
    )
    return jsonify({"salary": result}), 200


# ── Market Trends ──────────────────────────────────────────


@opportunities_bp.route("/market-trends", methods=["GET"])
def market_trends():
    trends = get_market_trends()
    return jsonify({"trends": trends}), 200


# ── Application Assistant ──────────────────────────────────


@opportunities_bp.route("/<int:opportunity_id>/application-readiness", methods=["GET"])
@login_required
def application_readiness(opportunity_id):
    from app.resume.models import Resume
    from app.career.services import build_career_memory

    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return jsonify({"error": "Not found"}), 404

    resume = Resume.query.filter_by(user_id=current_user.id).first()
    memory = build_career_memory(current_user.id)

    checks = []

    if not resume:
        checks.append(
            {
                "check": "Resume",
                "status": "fail",
                "message": "No resume found. Create one first.",
            }
        )
    elif not resume.summary:
        checks.append(
            {
                "check": "Resume Summary",
                "status": "warn",
                "message": "Add a professional summary to your resume",
            }
        )
    else:
        checks.append(
            {
                "check": "Resume",
                "status": "pass",
                "message": "Resume exists and looks complete",
            }
        )

    score_data = memory.get("score_history", [])
    if score_data:
        overall = (
            score_data[0].get("overall_score", 0)
            if isinstance(score_data[0], dict)
            else 0
        )
        if overall >= 60:
            checks.append(
                {
                    "check": "Career Score",
                    "status": "pass",
                    "message": f"Score: {overall}/100 — ready to apply",
                }
            )
        elif overall >= 40:
            checks.append(
                {
                    "check": "Career Score",
                    "status": "warn",
                    "message": f"Score: {overall}/100 — improve before applying aggressively",
                }
            )
        else:
            checks.append(
                {
                    "check": "Career Score",
                    "status": "warn",
                    "message": f"Score: {overall}/100 — strengthen your profile first",
                }
            )
    else:
        checks.append(
            {
                "check": "Career Score",
                "status": "info",
                "message": "Complete your profile to get a career score",
            }
        )

    match_score = calculate_match_score(current_user.id, opportunity_id)
    if match_score.get("overall_score", 0) >= 70:
        checks.append(
            {
                "check": "Job Match",
                "status": "pass",
                "message": f"Strong match ({match_score['overall_score']}%)",
            }
        )
    elif match_score.get("overall_score", 0) >= 40:
        checks.append(
            {
                "check": "Job Match",
                "status": "warn",
                "message": f"Moderate match ({match_score['overall_score']}%) — consider improving",
            }
        )
    else:
        checks.append(
            {
                "check": "Job Match",
                "status": "warn",
                "message": f"Low match ({match_score.get('overall_score', 0)}%) — focus on skill gaps first",
            }
        )

    ats = match_score.get("ats_match", 0)
    if ats >= 70:
        checks.append(
            {
                "check": "ATS Readiness",
                "status": "pass",
                "message": f"ATS score: {ats}% — resume is well-optimized",
            }
        )
    elif ats >= 40:
        checks.append(
            {
                "check": "ATS Readiness",
                "status": "warn",
                "message": f"ATS score: {ats}% — optimize resume keywords",
            }
        )
    else:
        checks.append(
            {
                "check": "ATS Readiness",
                "status": "warn",
                "message": f"ATS score: {ats}% — significant resume optimization needed",
            }
        )

    if resume and resume.skills and opp.tech_stack:
        user_skills = {s.lower() for s in resume.skills if isinstance(s, str)}
        job_skills = {s.lower() for s in opp.tech_stack if isinstance(s, str)}
        missing = job_skills - user_skills
        if not missing:
            checks.append(
                {
                    "check": "Skill Coverage",
                    "status": "pass",
                    "message": "You have all required skills",
                }
            )
        elif len(missing) <= 2:
            checks.append(
                {
                    "check": "Skill Coverage",
                    "status": "warn",
                    "message": f"Missing {len(missing)} skill(s): {', '.join(missing)}",
                }
            )
        else:
            checks.append(
                {
                    "check": "Skill Coverage",
                    "status": "warn",
                    "message": f"Missing {len(missing)} skills — review skill gap analysis",
                }
            )

    fail_count = sum(1 for c in checks if c["status"] == "fail")
    warn_count = sum(1 for c in checks if c["status"] == "warn")

    if fail_count > 0:
        verdict = "not_ready"
        verdict_message = "Complete the failed checks before applying"
    elif warn_count > 2:
        verdict = "almost_ready"
        verdict_message = "Address the warnings to improve your chances"
    elif warn_count > 0:
        verdict = "ready_with_caveats"
        verdict_message = "You can apply, but consider the warnings"
    else:
        verdict = "ready"
        verdict_message = "You're ready to apply! Good luck!"

    return jsonify(
        {
            "readiness": {
                "verdict": verdict,
                "message": verdict_message,
                "checks": checks,
                "overall_score": match_score.get("overall_score", 0),
            }
        }
    ), 200


# ── Recommendations ────────────────────────────────────────


@opportunities_bp.route("/recommendations", methods=["GET"])
@login_required
def get_opportunity_recommendations():
    from app.career.models import CareerProfile

    profile = CareerProfile.query.filter_by(user_id=current_user.id).first()

    q = Opportunity.query.filter_by(is_active=True)
    if profile and profile.target_role:
        q = q.filter(Opportunity.title.ilike(f"%{profile.target_role}%"))
    if profile and profile.target_location:
        q = q.filter(Opportunity.location.ilike(f"%{profile.target_location}%"))

    opportunities = q.order_by(Opportunity.created_at.desc()).limit(20).all()

    scored = []
    for opp in opportunities:
        match = calculate_match_score(current_user.id, opp.id)
        scored.append(
            {
                "opportunity": {
                    "id": opp.id,
                    "title": opp.title,
                    "company_name": opp.company_name,
                    "company_logo": opp.company_logo,
                    "location": opp.location,
                    "remote_type": opp.remote_type,
                    "salary_min": opp.salary_min,
                    "salary_max": opp.salary_max,
                    "currency": opp.currency,
                    "employment_type": opp.employment_type,
                    "tech_stack": opp.tech_stack or [],
                },
                "match_score": match,
            }
        )

    scored.sort(key=lambda x: x["match_score"].get("overall_score", 0), reverse=True)

    return jsonify({"recommendations": scored[:10]}), 200
