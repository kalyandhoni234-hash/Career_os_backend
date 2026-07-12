import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.career.models import (
    CareerProfile,
    CareerGoal,
    Roadmap,
    RoadmapNode,
    CareerTimelineEvent,
    AIRecommendation,
    CareerReport,
    CareerScoreSnapshot,
)
from app.career.services import (
    build_career_memory,
    compute_career_score,
    generate_recommendations,
    get_action_center,
    generate_roadmap,
    get_roadmap_with_nodes,
    update_roadmap_progress,
    build_skill_graph,
    analyze_skill_gaps,
    generate_weekly_report,
    get_previous_reports,
    build_ai_profile,
    generate_personalized_roadmap,
    get_roadmap_with_progress,
    update_lesson_progress,
    get_dashboard_roadmap,
    get_available_career_paths,
    recommend_next_lesson,
)
from app.extensions import db

logger = logging.getLogger(__name__)

career_bp = Blueprint("career", __name__)


# ── Health ────────────────────────────────────────────────


@career_bp.route("/ping")
def ping():
    return {"blueprint": "career", "status": "alive"}


# ── Career Memory ─────────────────────────────────────────


@career_bp.route("/memory", methods=["GET"])
@login_required
def get_career_memory():
    memory = build_career_memory(current_user.id)
    return jsonify({"memory": memory}), 200


# ── AI Profile Engine ─────────────────────────────────────


@career_bp.route("/profile", methods=["GET"])
@login_required
def get_ai_profile():
    profile = build_ai_profile(current_user.id)
    return jsonify({"profile": profile}), 200


@career_bp.route("/profile", methods=["POST", "PUT"])
@login_required
def update_career_profile():
    data = request.get_json(silent=True) or {}
    cp = CareerProfile.query.filter_by(user_id=current_user.id).first()
    if not cp:
        cp = CareerProfile(user_id=current_user.id)
        db.session.add(cp)

    for field in [
        "target_role",
        "target_company",
        "target_location",
        "target_salary",
        "career_level",
        "years_experience",
        "career_goal_type",
    ]:
        if field in data:
            setattr(cp, field, data[field])
    for field in ["preferred_roles", "preferred_locations", "interests"]:
        if field in data and isinstance(data[field], list):
            setattr(cp, field, data[field])

    db.session.commit()

    from app.core.integration import on_profile_changed
    on_profile_changed(current_user.id)

    return jsonify({"message": "Career profile saved"}), 200


# ── Career Score ──────────────────────────────────────────


@career_bp.route("/score", methods=["GET"])
@login_required
def get_career_score():
    score = compute_career_score(current_user.id)
    history = [
        {
            "overall_score": s.overall_score,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "breakdown": s.breakdown,
        }
        for s in CareerScoreSnapshot.query.filter_by(user_id=current_user.id)
        .order_by(CareerScoreSnapshot.created_at.desc())
        .limit(30)
        .all()
    ]
    return jsonify({"score": score, "history": history}), 200


# ── Action Center ─────────────────────────────────────────


@career_bp.route("/action-center", methods=["GET"])
@login_required
def get_action_center_endpoint():
    plan = get_action_center(current_user.id)
    if not plan:
        generate_recommendations(current_user.id, force=True)
        plan = get_action_center(current_user.id)
    return jsonify({"plan": plan}), 200


# ── Smart Recommendations ─────────────────────────────────


@career_bp.route("/recommendations", methods=["GET"])
@login_required
def get_recommendations():
    force = request.args.get("force", "false").lower() == "true"
    recs = generate_recommendations(current_user.id, force=force)
    return jsonify({"recommendations": recs}), 200


@career_bp.route("/recommendations/<int:rec_id>/dismiss", methods=["POST"])
@login_required
def dismiss_recommendation(rec_id):
    rec = AIRecommendation.query.filter_by(id=rec_id, user_id=current_user.id).first()
    if not rec:
        return jsonify({"error": "Recommendation not found"}), 404
    rec.is_dismissed = True
    db.session.commit()
    return jsonify({"message": "Recommendation dismissed"}), 200


@career_bp.route("/recommendations/<int:rec_id>/complete", methods=["POST"])
@login_required
def complete_recommendation(rec_id):
    rec = AIRecommendation.query.filter_by(id=rec_id, user_id=current_user.id).first()
    if not rec:
        return jsonify({"error": "Recommendation not found"}), 404
    rec.is_completed = True
    db.session.commit()

    # Log as timeline event
    event = CareerTimelineEvent(
        user_id=current_user.id,
        event_type="recommendation",
        title=f"Completed: {rec.title}",
        description=rec.description or "",
        event_date=datetime.now(timezone.utc),
        importance=rec.priority,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({"message": "Recommendation completed"}), 200


# ── Learning Roadmaps ─────────────────────────────────────


@career_bp.route("/roadmaps", methods=["GET"])
@login_required
def list_roadmaps():
    roadmaps = (
        Roadmap.query.filter_by(user_id=current_user.id)
        .order_by(Roadmap.created_at.desc())
        .all()
    )
    result = []
    for r in roadmaps:
        nodes = RoadmapNode.query.filter_by(roadmap_id=r.id).all()
        completed = sum(1 for n in nodes if n.status == "completed")
        total = len(nodes)
        result.append(
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "category": r.category,
                "target_role": r.target_role,
                "progress": r.progress or 0,
                "estimated_weeks": r.estimated_weeks,
                "status": r.status,
                "completed_nodes": completed,
                "total_nodes": total,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return jsonify({"roadmaps": result}), 200


@career_bp.route("/roadmaps/generate", methods=["POST"])
@login_required
def create_roadmap():
    user_id = current_user.id
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    target_role = data.get("target_role")
    logger.info(
        "Generating roadmap for user %s: category=%s, target_role=%s",
        user_id,
        category,
        target_role,
    )
    try:
        roadmap = generate_roadmap(user_id, category=category, target_role=target_role)
    except Exception as e:
        logger.error(
            "Roadmap generation failed for user %s: %s", user_id, str(e), exc_info=True
        )
        return jsonify({"error": "Failed to generate roadmap", "reason": str(e)}), 500
    if not roadmap:
        return jsonify(
            {
                "error": "Failed to generate roadmap",
                "reason": "generate_roadmap returned None",
            }
        ), 500
    return jsonify({"roadmap": roadmap}), 201


@career_bp.route("/roadmaps/<int:roadmap_id>", methods=["GET"])
@login_required
def get_roadmap(roadmap_id):
    roadmap = get_roadmap_with_nodes(roadmap_id)
    if not roadmap:
        return jsonify({"error": "Roadmap not found"}), 404
    # Verify ownership
    r = Roadmap.query.get(roadmap_id)
    if r and r.user_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"roadmap": roadmap}), 200


@career_bp.route("/roadmaps/node/<int:node_id>/progress", methods=["PUT"])
@login_required
def update_node_progress(node_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status", "completed")
    result = update_roadmap_progress(current_user.id, node_id, status)
    if not result:
        return jsonify({"error": "Node not found"}), 404

    from app.core.integration import on_roadmap_progress_changed
    on_roadmap_progress_changed(current_user.id, node_id)

    return jsonify({"roadmap": result}), 200


@career_bp.route("/roadmaps/<int:roadmap_id>", methods=["DELETE"])
@login_required
def delete_roadmap(roadmap_id):
    roadmap = Roadmap.query.filter_by(id=roadmap_id, user_id=current_user.id).first()
    if not roadmap:
        return jsonify({"error": "Roadmap not found"}), 404
    db.session.delete(roadmap)
    db.session.commit()
    return jsonify({"message": "Roadmap deleted"}), 200


# ── Personalized Roadmap Engine ──────────────────────────


@career_bp.route("/career-paths", methods=["GET"])
@login_required
def list_career_paths():
    try:
        paths = get_available_career_paths()
        return jsonify({"paths": paths}), 200
    except Exception as e:
        logger.error("Failed to list career paths for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({"error": "Failed to load career paths"}), 500


@career_bp.route("/my-roadmap", methods=["GET"])
@login_required
def get_my_roadmap():
    """Get the user's active personalized roadmap (for dashboard display)."""
    try:
        dashboard = get_dashboard_roadmap(current_user.id)
        return jsonify({"roadmap": dashboard}), 200
    except Exception as e:
        logger.error("Failed to get dashboard roadmap for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({"error": "Failed to load roadmap data", "roadmap": None}), 200


@career_bp.route("/roadmaps/auto-generate", methods=["POST"])
@login_required
def auto_generate_personalized_roadmap():
    """Auto-generate or refresh a personalized roadmap from onboarding data."""
    try:
        data = request.get_json(silent=True) or {}
        target_role = data.get("target_role")
        result = generate_personalized_roadmap(current_user.id, target_role=target_role)
        if not result:
            return jsonify({"error": "Could not generate roadmap. No target role set or no matching roadmap definition."}), 400
        return jsonify({"roadmap": result}), 201
    except Exception as e:
        logger.error("Auto-generate roadmap failed for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({"error": "Failed to generate roadmap"}), 500


@career_bp.route("/roadmaps/<int:roadmap_id>/full", methods=["GET"])
@login_required
def get_full_roadmap(roadmap_id):
    """Get a full roadmap with phases, modules, lessons and progress."""
    try:
        roadmap = Roadmap.query.get(roadmap_id)
        if not roadmap or roadmap.user_id != current_user.id:
            return jsonify({"error": "Roadmap not found"}), 404
        result = get_roadmap_with_progress(roadmap_id)
        if not result:
            return jsonify({"error": "Roadmap data not available"}), 500
        return jsonify({"roadmap": result}), 200
    except Exception as e:
        logger.error("Failed to get full roadmap %s for user %s: %s", roadmap_id, current_user.id, e, exc_info=True)
        return jsonify({"error": "Failed to load roadmap details"}), 500


@career_bp.route("/roadmaps/<int:roadmap_id>/lesson/<lesson_id>/progress", methods=["PUT"])
@login_required
def update_lesson_progress_endpoint(roadmap_id, lesson_id):
    """Update progress for a specific lesson (not_started, in_progress, completed, skipped, need_revision)."""
    try:
        data = request.get_json(silent=True) or {}
        status = data.get("status", "completed")
        score = data.get("score")
        notes = data.get("notes")
        result = update_lesson_progress(current_user.id, roadmap_id, lesson_id, status, score, notes)
        if not result:
            return jsonify({"error": "Lesson or roadmap not found"}), 404

        from app.core.integration import on_roadmap_progress_changed
        on_roadmap_progress_changed(current_user.id, 0)

        return jsonify({"roadmap": result}), 200
    except Exception as e:
        logger.error("Failed to update lesson progress for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({"error": "Failed to update lesson progress"}), 500


@career_bp.route("/roadmaps/<int:roadmap_id>/lesson/<lesson_id>/recommendations", methods=["GET"])
@login_required
def get_lesson_recommendations(roadmap_id, lesson_id):
    """Get AI recommendations after completing a lesson."""
    try:
        recs = recommend_next_lesson(roadmap_id, lesson_id)
        return jsonify(recs), 200
    except Exception as e:
        logger.error("Failed to get recommendations for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({"next_lesson": None, "projects": [], "resources": []}), 200


# ── Skill Graph ───────────────────────────────────────────


@career_bp.route("/skill-graph", methods=["GET"])
@login_required
def get_skill_graph():
    graph = build_skill_graph(current_user.id)
    return jsonify({"graph": graph}), 200


# ── Skill Gap Analysis ────────────────────────────────────


@career_bp.route("/skill-gaps", methods=["GET"])
@login_required
def get_skill_gaps():
    target_role = request.args.get("target_role")
    analysis = analyze_skill_gaps(current_user.id, target_role=target_role)
    return jsonify(analysis), 200


# ── Project Recommendations ───────────────────────────────


@career_bp.route("/project-recommendations", methods=["GET"])
@login_required
def get_project_recommendations():
    gaps = analyze_skill_gaps(current_user.id)
    projects = []
    for gap in gaps.get("gaps", [])[:6]:
        projects.append(
            {
                "skill": gap["skill"],
                "project": gap.get("recommended_project", ""),
                "estimated_ats_gain": gap.get("estimated_ats_gain", 0),
                "priority": gap.get("priority", 0),
            }
        )
    return jsonify({"projects": projects}), 200


# ── Career Timeline ───────────────────────────────────────


@career_bp.route("/timeline", methods=["GET"])
@login_required
def get_timeline():
    from app.resume.models import Resume
    from app.jobs.models import Job

    events = []

    # Resume-based events
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if resume:
        if resume.created_at:
            events.append(
                {
                    "event_type": "resume",
                    "title": "Resume Created",
                    "description": "Started building your resume",
                    "event_date": resume.created_at.isoformat(),
                    "importance": 3,
                }
            )
        if resume.experience:
            for exp in resume.experience:
                if exp.get("start"):
                    events.append(
                        {
                            "event_type": "experience",
                            "title": f"{exp.get('role', 'Role')} at {exp.get('company', 'Company')}",
                            "description": exp.get("start", "")
                            + " - "
                            + exp.get("end", "Present"),
                            "event_date": exp.get("start", ""),
                            "importance": 2,
                        }
                    )
        if resume.education:
            for edu in resume.education:
                if edu.get("start"):
                    events.append(
                        {
                            "event_type": "education",
                            "title": f"{edu.get('degree', 'Degree')} at {edu.get('school', 'School')}",
                            "description": edu.get("field", ""),
                            "event_date": edu.get("start", ""),
                            "importance": 2,
                        }
                    )
        if resume.projects:
            events.append(
                {
                    "event_type": "project",
                    "title": f"{len(resume.projects)} project(s) added",
                    "description": "Projects added to resume",
                    "event_date": resume.updated_at.isoformat()
                    if resume.updated_at
                    else "",
                    "importance": 2,
                }
            )

    # Application events
    jobs = Job.query.filter_by(user_id=current_user.id).all()
    for job in jobs:
        if job.status == "offer":
            events.append(
                {
                    "event_type": "offer",
                    "title": f"Offer from {job.company}",
                    "description": f"Received offer for {job.role}",
                    "event_date": job.updated_at.isoformat() if job.updated_at else "",
                    "importance": 5,
                }
            )
        elif job.status == "interview":
            events.append(
                {
                    "event_type": "interview",
                    "title": f"Interview at {job.company}",
                    "description": f"Interviewed for {job.role}",
                    "event_date": job.updated_at.isoformat() if job.updated_at else "",
                    "importance": 4,
                }
            )
        else:
            events.append(
                {
                    "event_type": "application",
                    "title": f"Applied to {job.company}",
                    "description": f"Applied for {job.role}",
                    "event_date": job.created_at.isoformat() if job.created_at else "",
                    "importance": 1,
                }
            )

    # Stored timeline events
    stored = (
        CareerTimelineEvent.query.filter_by(user_id=current_user.id)
        .order_by(CareerTimelineEvent.event_date.desc())
        .all()
    )
    for e in stored:
        events.append(
            {
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description or "",
                "event_date": e.event_date.isoformat() if e.event_date else "",
                "importance": e.importance,
                "metadata": e.metadata_json,
            }
        )

    # Sort by date descending
    def parse_date(e):
        try:
            return e.get("event_date", "")
        except Exception:
            return ""

    events.sort(key=parse_date, reverse=True)

    # Stats
    years_active = set()
    for e in events:
        d = e.get("event_date", "")
        if d and len(d) >= 4:
            try:
                years_active.add(d[:4])
            except Exception as e:
                logger.warning("Failed to parse event date: %s", e)

    return jsonify(
        {
            "events": events[:50],
            "total_events": len(events),
            "years_active": sorted(years_active) if years_active else [],
        }
    ), 200


# ── Smart Goals ───────────────────────────────────────────


@career_bp.route("/goals", methods=["GET"])
@login_required
def list_goals():
    goals = (
        CareerGoal.query.filter_by(user_id=current_user.id)
        .order_by(CareerGoal.priority.desc(), CareerGoal.created_at.desc())
        .all()
    )
    return jsonify(
        {
            "goals": [
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description,
                    "target_role": g.target_role,
                    "target_company": g.target_company,
                    "target_date": g.target_date.isoformat() if g.target_date else None,
                    "status": g.status,
                    "priority": g.priority,
                    "progress": g.progress,
                    "category": g.category,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                }
                for g in goals
            ]
        }
    ), 200


@career_bp.route("/goals", methods=["POST"])
@login_required
def create_goal():
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "Title is required"}), 400
    goal = CareerGoal(
        user_id=current_user.id,
        title=data["title"],
        description=data.get("description", ""),
        target_role=data.get("target_role"),
        target_company=data.get("target_company"),
        target_date=datetime.strptime(data["target_date"], "%Y-%m-%d").date()
        if data.get("target_date")
        else None,
        priority=data.get("priority", 3),
        category=data.get("category", "career"),
    )
    db.session.add(goal)
    db.session.flush()

    # Log timeline event
    event = CareerTimelineEvent(
        user_id=current_user.id,
        event_type="goal",
        title=f"Set goal: {goal.title}",
        description=data.get("description", ""),
        event_date=datetime.now(timezone.utc),
        importance=goal.priority,
    )
    db.session.add(event)
    db.session.commit()

    return jsonify(
        {
            "goal": {
                "id": goal.id,
                "title": goal.title,
                "description": goal.description,
                "target_role": goal.target_role,
                "target_company": goal.target_company,
                "target_date": goal.target_date.isoformat()
                if goal.target_date
                else None,
                "status": goal.status,
                "priority": goal.priority,
                "progress": goal.progress,
                "category": goal.category,
            }
        }
    ), 201


@career_bp.route("/goals/<int:goal_id>", methods=["PUT"])
@login_required
def update_goal(goal_id):
    goal = CareerGoal.query.filter_by(id=goal_id, user_id=current_user.id).first()
    if not goal:
        return jsonify({"error": "Goal not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in [
        "title",
        "description",
        "target_role",
        "target_company",
        "status",
        "priority",
        "progress",
        "category",
    ]:
        if field in data:
            setattr(goal, field, data[field])
    if data.get("target_date"):
        goal.target_date = datetime.strptime(data["target_date"], "%Y-%m-%d").date()
    db.session.commit()
    return jsonify({"message": "Goal updated"}), 200


@career_bp.route("/goals/<int:goal_id>", methods=["DELETE"])
@login_required
def delete_goal(goal_id):
    goal = CareerGoal.query.filter_by(id=goal_id, user_id=current_user.id).first()
    if not goal:
        return jsonify({"error": "Goal not found"}), 404
    db.session.delete(goal)
    db.session.commit()
    from app.core.integration import on_profile_changed
    on_profile_changed(current_user.id)
    return jsonify({"message": "Goal deleted"}), 200


# ── Weekly Reports ────────────────────────────────────────


@career_bp.route("/reports", methods=["GET"])
@login_required
def list_reports():
    reports = get_previous_reports(current_user.id)
    return jsonify({"reports": reports}), 200


@career_bp.route("/reports/generate", methods=["POST"])
@login_required
def create_report():
    report = generate_weekly_report(current_user.id)
    return jsonify({"report": report}), 201


@career_bp.route("/reports/<int:report_id>", methods=["GET"])
@login_required
def get_report(report_id):
    report = CareerReport.query.filter_by(id=report_id, user_id=current_user.id).first()
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(
        {
            "report": {
                "id": report.id,
                "week_start": report.week_start.isoformat()
                if report.week_start
                else None,
                "week_end": report.week_end.isoformat() if report.week_end else None,
                "score_before": report.score_before,
                "score_after": report.score_after,
                "metrics": report.metrics,
                "achievements": report.achievements or [],
                "recommendations": report.recommendations or [],
                "summary": report.summary or "",
                "created_at": report.created_at.isoformat()
                if report.created_at
                else None,
            }
        }
    ), 200


# ── Dashboard Data ────────────────────────────────────────


@career_bp.route("/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    """Aggregated dashboard data combining all career modules."""
    user_id = current_user.id
    logger.info("Fetching career dashboard for user %s", user_id)
    try:
        score = compute_career_score(user_id)
        profile = build_ai_profile(user_id)
        plan = get_action_center(user_id)
        graph = build_skill_graph(user_id)
        memory = build_career_memory(user_id)
    except Exception as e:
        logger.error(
            "Dashboard data pipeline failed for user %s: %s",
            user_id,
            str(e),
            exc_info=True,
        )
        return jsonify(
            {"error": "Failed to build dashboard data", "reason": str(e)}
        ), 500

    try:
        roadmaps = Roadmap.query.filter_by(user_id=user_id, status="active").all()
        roadmap_data = [
            {
                "id": r.id,
                "title": r.title,
                "progress": r.progress or 0,
                "estimated_weeks": r.estimated_weeks,
                "category": r.category,
            }
            for r in roadmaps
        ]
        goals = [
            {
                "id": g.id,
                "title": g.title,
                "target_role": g.target_role,
                "target_company": g.target_company,
                "progress": g.progress,
            }
            for g in CareerGoal.query.filter_by(user_id=user_id, status="active")
            .order_by(CareerGoal.priority.desc())
            .limit(5)
            .all()
        ]
    except Exception as e:
        logger.error(
            "Dashboard DB queries failed for user %s: %s",
            user_id,
            str(e),
            exc_info=True,
        )
        return jsonify({"error": "Dashboard database error", "reason": str(e)}), 500

    return jsonify(
        {
            "score": score,
            "profile": profile,
            "action_plan": plan[:8] if plan else [],
            "skill_graph": graph,
            "roadmaps": roadmap_data,
            "recent_timeline_events": memory.get("timeline", [])[:5],
            "goals": goals,
        }
    ), 200
