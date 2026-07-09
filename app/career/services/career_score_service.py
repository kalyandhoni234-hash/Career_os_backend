from app.extensions import db
from app.career.models import CareerScoreSnapshot


def compute_career_score(user_id):
    """Compute and persist a unified Career Score from all data sources."""
    from app.resume.models import Resume
    from app.jobs.models import Job
    from app.career.models import LearningProgress, SkillGraph, Roadmap

    resume = Resume.query.filter_by(user_id=user_id).first()
    jobs = Job.query.filter_by(user_id=user_id).all() if user_id else []
    learning = LearningProgress.query.filter_by(user_id=user_id).all()
    skill_cats = SkillGraph.query.filter_by(user_id=user_id).all()
    roadmaps = Roadmap.query.filter_by(user_id=user_id).all()

    # 1. Resume Score (0-100) - completeness
    resume_score = 0
    if resume:
        fields = [
            resume.full_name, resume.email, resume.summary,
            resume.experience, resume.education, resume.skills,
            resume.projects,
        ]
        filled = sum(1 for f in fields if f)
        resume_score = int((filled / len(fields)) * 100)
        # Bonus for having more content
        exp_count = len(resume.experience or [])
        proj_count = len(resume.projects or [])
        resume_score = min(100, resume_score + (exp_count * 2) + (proj_count * 1))

    # 2. ATS Score (0-100)
    ats_score = 0
    if resume and resume.target_job_description:
        from app.resume.ats import score_resume
        try:
            ats_result = score_resume(resume, resume.target_job_description)
            ats_score = ats_result.get("overall_score", 0)
        except Exception:
            ats_score = 0

    # 3. Projects Score (0-100)
    proj_count = len(resume.projects or []) if resume else 0
    projects_score = min(100, proj_count * 25)

    # 4. Applications Score (0-100)
    total_apps = len(jobs)
    offers = sum(1 for j in jobs if j.status == "offer")
    interviews = sum(1 for j in jobs if j.status in ("interview", "offer"))
    apps_score = min(100, total_apps * 5)
    if offers > 0:
        apps_score = min(100, apps_score + 20)
    if interviews > 0:
        apps_score = min(100, apps_score + (interviews * 5))

    # 5. Learning Score (0-100)
    if learning:
        avg_prof = sum(lp.proficiency for lp in learning) / len(learning)
        learning_score = int(avg_prof)
    else:
        learning_score = 0

    # 6. Interview Score (0-100)
    if total_apps > 0 and interviews > 0:
        interview_rate = (interviews / total_apps) * 100
    else:
        interview_rate = 0
    interview_score = min(100, int(interview_rate))

    # 7. Skill Coverage (0-100)
    if skill_cats:
        avg_skill = sum(sg.proficiency for sg in skill_cats) / len(skill_cats)
        skill_coverage = int(avg_skill)
    else:
        skill_coverage = 0

    # 8. Roadmap Progress (bonus)
    roadmap_bonus = 0
    if roadmaps:
        avg_progress = sum(r.progress for r in roadmaps) / len(roadmaps)
        roadmap_bonus = int(avg_progress * 0.1)

    # Weighted overall score
    overall = int(
        resume_score * 0.25 +
        ats_score * 0.20 +
        projects_score * 0.10 +
        apps_score * 0.15 +
        learning_score * 0.10 +
        interview_score * 0.10 +
        skill_coverage * 0.10 +
        roadmap_bonus
    )
    overall = max(0, min(100, overall))

    breakdown = {
        "resume_score": resume_score,
        "ats_score": ats_score,
        "projects_score": projects_score,
        "applications_score": apps_score,
        "learning_score": learning_score,
        "interview_score": interview_score,
        "skill_coverage": skill_coverage,
        "roadmap_bonus": roadmap_bonus,
    }

    # Persist snapshot
    snapshot = CareerScoreSnapshot(
        user_id=user_id,
        overall_score=overall,
        resume_score=resume_score,
        ats_score=ats_score,
        projects_score=projects_score,
        applications_score=apps_score,
        learning_score=learning_score,
        interview_score=interview_score,
        skill_coverage=skill_coverage,
        breakdown=breakdown,
    )
    db.session.add(snapshot)
    db.session.commit()

    return {
        "overall_score": overall,
        "breakdown": breakdown,
        "snapshot_id": snapshot.id,
        "timestamp": snapshot.created_at.isoformat() if snapshot.created_at else None,
    }
