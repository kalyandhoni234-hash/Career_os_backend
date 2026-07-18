import logging
from datetime import datetime, timezone
from app.career.models import (
    CareerProfile,
    CareerGoal,
    Roadmap,
    LearningProgress,
    SkillGraph,
    CareerTimelineEvent,
    AIRecommendation,
    CareerScoreSnapshot,
)

logger = logging.getLogger(__name__)


def build_career_memory(user_id):
    """Build a structured Career Memory context from all user data sources."""
    memory = {
        "profile": _get_profile_data(user_id),
        "career_profile": _get_career_profile(user_id),
        "resume": _get_resume_data(user_id),
        "ats": _get_ats_data(user_id),
        "applications": _get_application_data(user_id),
        "skills": _get_skill_data(user_id),
        "learning": _get_learning_data(user_id),
        "goals": _get_goal_data(user_id),
        "roadmaps": _get_roadmap_data(user_id),
        "timeline": _get_timeline_data(user_id),
        "recent_coach": _get_recent_coach_data(user_id),
        "score_history": _get_score_history(user_id),
        "recommendations": _get_recommendation_data(user_id),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    return memory


def _get_profile_data(user_id):
    from app.users.models import Profile

    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return {}
    return {
        "education": profile.education or "",
        "degree": profile.degree or "",
        "graduation_year": profile.graduation_year,
        "country": profile.country or "",
        "preferred_roles": profile.preferred_roles or [],
        "skills": profile.skills or [],
        "experience": profile.experience or "",
        "languages": profile.languages or [],
        "interests": profile.interests or [],
        "preferred_locations": profile.preferred_locations or [],
        "salary_expectation": profile.salary_expectation or "",
    }


def _get_career_profile(user_id):
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    if not cp:
        return {}
    return {
        "target_role": cp.target_role or "",
        "target_company": cp.target_company or "",
        "target_location": cp.target_location or "",
        "target_salary": cp.target_salary or "",
        "career_level": cp.career_level or "student",
        "years_experience": cp.years_experience or 0,
        "career_goal_type": cp.career_goal_type or "internship",
    }


def _get_resume_data(user_id):
    from app.resume.models import Resume, ResumeVersion

    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        return {}
    versions = (
        ResumeVersion.query.filter_by(resume_id=resume.id)
        .order_by(ResumeVersion.created_at.desc())
        .all()
    )
    latest_version = None
    if versions:
        v = versions[0]
        latest_version = {
            "id": v.id,
            "version_name": v.version_name,
            "source": v.source or "manual",
            "target_role": v.target_role or "",
            "ats_score": v.ats_score,
            "notes": v.notes or "",
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        }
    return {
        "full_name": resume.full_name or "",
        "title": resume.title or "",
        "summary": resume.summary or "",
        "skills": resume.skills or [],
        "experience_entries": len(resume.experience or []),
        "projects": len(resume.projects or []),
        "education_entries": len(resume.education or []),
        "certificates": len(resume.certificates or []),
        "languages": resume.languages or [],
        "has_resume": True,
        "tone": resume.tone or "professional",
        "version_count": len(versions),
        "latest_version": latest_version,
    }


def _get_ats_data(user_id):
    from app.resume.models import Resume

    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        return {}
    ats = None
    if resume.target_job_description:
        from app.resume.ats import score_resume

        try:
            ats = score_resume(resume, resume.target_job_description)
        except Exception:
            ats = None
    if ats:
        return {
            "overall_score": ats.get("overall_score", 0),
            "keyword_match": ats.get("keyword_match", 0),
            "matched_skills": ats.get("matched", []),
            "missing_skills": ats.get("missing", []),
            "action_verb_score": ats.get("action_verb_score", 0),
            "strong_verbs": ats.get("strong_verbs", []),
            "weak_verbs": ats.get("weak_verbs", []),
        }
    return {"overall_score": 0, "keyword_match": 0, "missing_skills": []}


def _get_application_data(user_id):
    from app.jobs.models import Job

    jobs = Job.query.filter_by(user_id=user_id).all()
    total = len(jobs)
    by_status = {}
    for j in jobs:
        by_status[j.status] = by_status.get(j.status, 0) + 1
    interviews = sum(1 for j in jobs if j.status in ("interview", "offer"))
    offers = sum(1 for j in jobs if j.status == "offer")
    return {
        "total_applications": total,
        "by_status": by_status,
        "interview_count": interviews,
        "offer_count": offers,
        "active_applications": sum(
            1 for j in jobs if j.status in ("applied", "oa", "interview")
        ),
    }


def _get_skill_data(user_id):
    from app.resume.models import Resume

    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        raw = []
    else:
        raw = resume.skills_list
    if isinstance(raw, str):
        raw = [raw]
    clean = []
    for s in raw:
        if isinstance(s, str):
            s = s.strip()
            if not s or len(s) > 50:
                continue
            clean.append(s)
    resume_skills = set(clean)
    skill_graphs = SkillGraph.query.filter_by(user_id=user_id).all()
    graph_data = {
        sg.category: {"proficiency": sg.proficiency, "count": sg.skill_count}
        for sg in skill_graphs
    }
    learning = LearningProgress.query.filter_by(user_id=user_id).all()
    learning_skills = {lp.skill_name: lp.proficiency for lp in learning}
    return {
        "resume_skills": sorted(resume_skills),
        "skill_graph": graph_data,
        "learning_progress": learning_skills,
        "total_skills": len(resume_skills),
    }


def _get_learning_data(user_id):
    progress = LearningProgress.query.filter_by(user_id=user_id).all()
    return [
        {"skill": p.skill_name, "proficiency": p.proficiency, "category": p.category}
        for p in progress
    ]


def _get_goal_data(user_id):
    goals = CareerGoal.query.filter_by(user_id=user_id, status="active").all()
    completed = CareerGoal.query.filter_by(user_id=user_id, status="completed").count()
    return {
        "active_goals": [
            {
                "id": g.id,
                "title": g.title,
                "target_role": g.target_role,
                "target_company": g.target_company,
                "progress": g.progress,
                "priority": g.priority,
            }
            for g in goals
        ],
        "completed_goals": completed,
        "total_goals": CareerGoal.query.filter_by(user_id=user_id).count(),
    }


def _get_roadmap_data(user_id):
    roadmaps = Roadmap.query.filter_by(user_id=user_id).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "category": r.category,
            "progress": r.progress,
            "estimated_weeks": r.estimated_weeks,
            "status": r.status,
        }
        for r in roadmaps
    ]


def _get_timeline_data(user_id):
    events = (
        CareerTimelineEvent.query.filter_by(user_id=user_id)
        .order_by(CareerTimelineEvent.event_date.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "type": e.event_type,
            "title": e.title,
            "date": e.event_date.isoformat() if e.event_date else None,
            "importance": e.importance,
        }
        for e in events
    ]


def _get_recent_coach_data(user_id):
    from app.coach.models import CoachMessage

    recent = (
        CoachMessage.query.filter_by(user_id=user_id, role="assistant")
        .order_by(CoachMessage.created_at.desc())
        .limit(3)
        .all()
    )
    return [
        {
            "content": m.content[:200],
            "timestamp": m.created_at.isoformat() if m.created_at else None,
        }
        for m in recent
    ]


def _get_score_history(user_id):
    snapshots = (
        CareerScoreSnapshot.query.filter_by(user_id=user_id)
        .order_by(CareerScoreSnapshot.created_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "overall_score": s.overall_score,
            "date": s.created_at.isoformat() if s.created_at else None,
            "breakdown": s.breakdown,
        }
        for s in snapshots
    ]


def _get_recommendation_data(user_id):
    recs = (
        AIRecommendation.query.filter_by(
            user_id=user_id, is_dismissed=False, is_completed=False
        )
        .order_by(
            AIRecommendation.priority.desc(), AIRecommendation.impact_score.desc()
        )
        .limit(10)
        .all()
    )
    return [
        {
            "type": r.rec_type,
            "title": r.title,
            "description": r.description,
            "priority": r.priority,
            "impact_score": r.impact_score,
            "category": r.category,
        }
        for r in recs
    ]
