import logging
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.agents.models import CareerAgent, AgentTask, AGENT_TYPES

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULES = {
    "job_discovery": timedelta(hours=6),
    "resume_optimization": timedelta(days=1),
    "ats_intelligence": timedelta(hours=12),
    "opportunity_ranking": timedelta(hours=6),
    "company_intelligence": timedelta(days=1),
    "salary_intelligence": timedelta(days=1),
    "learning": timedelta(days=1),
    "project_recommendation": timedelta(days=2),
    "interview_preparation": timedelta(hours=12),
    "networking": timedelta(days=3),
    "notification": timedelta(hours=1),
    "weekly_report": timedelta(days=7),
    "career_strategy": timedelta(days=1),
}


def ensure_default_agents(user_id):
    """Create default agents for a user if they don't exist."""
    for agent_type in AGENT_TYPES:
        existing = CareerAgent.query.filter_by(
            user_id=user_id, agent_type=agent_type
        ).first()
        if not existing:
            schedule = DEFAULT_SCHEDULES.get(agent_type, timedelta(days=1))
            agent = CareerAgent(
                user_id=user_id,
                agent_type=agent_type,
                status="idle",
                next_run_at=datetime.now(timezone.utc) + schedule,
                config={"schedule_minutes": int(schedule.total_seconds() / 60)},
            )
            db.session.add(agent)
    db.session.commit()
    return (
        CareerAgent.query.filter_by(user_id=user_id)
        .order_by(CareerAgent.agent_type)
        .all()
    )


def get_agent_statuses(user_id):
    """Return all agents with their current status for a user."""
    agents = (
        CareerAgent.query.filter_by(user_id=user_id)
        .order_by(CareerAgent.agent_type)
        .all()
    )
    if not agents:
        agents = ensure_default_agents(user_id)
    result = []
    for a in agents:
        pending_tasks = AgentTask.query.filter_by(
            agent_id=a.id, status="pending"
        ).count()
        running_tasks = AgentTask.query.filter_by(
            agent_id=a.id, status="running"
        ).count()
        result.append(
            {
                "id": a.id,
                "agent_type": a.agent_type,
                "status": a.status,
                "last_run_at": a.last_run_at.isoformat() if a.last_run_at else None,
                "next_run_at": a.next_run_at.isoformat() if a.next_run_at else None,
                "total_runs": a.total_runs,
                "total_errors": a.total_errors,
                "config": a.config,
                "pending_tasks": pending_tasks,
                "running_tasks": running_tasks,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    return result


def get_agent_by_type(user_id, agent_type):
    """Get a specific agent by type."""
    return CareerAgent.query.filter_by(user_id=user_id, agent_type=agent_type).first()


def get_recent_tasks(user_id, limit=20):
    """Return recent tasks for a user, newest first."""
    tasks = (
        AgentTask.query.filter_by(user_id=user_id)
        .order_by(AgentTask.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": t.id,
            "agent_id": t.agent_id,
            "task_type": t.task_type,
            "status": t.status,
            "priority": t.priority,
            "progress": t.progress,
            "error_message": t.error_message,
            "scheduled_at": t.scheduled_at.isoformat() if t.scheduled_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


def run_agent(user_id, agent_type):
    """Trigger a specific agent to run. Creates a task and marks agent as running."""
    agent = get_agent_by_type(user_id, agent_type)
    if not agent:
        agent = ensure_default_agents(user_id)
        agent = get_agent_by_type(user_id, agent_type)
    if not agent:
        return None

    if agent.status == "running":
        return {"error": "Agent is already running"}

    agent.status = "running"
    agent.total_runs += 1

    task = AgentTask(
        user_id=user_id,
        agent_id=agent.id,
        task_type=f"{agent_type}_scan",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.session.add(task)
    db.session.commit()

    try:
        result = _execute_agent_task(agent_type, user_id)
        task.status = "completed"
        task.output_data = result or {}
        task.completed_at = datetime.now(timezone.utc)
        task.progress = 100
        agent.status = "idle"
        agent.last_run_at = datetime.now(timezone.utc)
        schedule = DEFAULT_SCHEDULES.get(agent_type, timedelta(days=1))
        agent.next_run_at = datetime.now(timezone.utc) + schedule
        db.session.commit()
        return {"task_id": task.id, "status": "completed", "result": result}
    except Exception as e:
        db.session.rollback()
        logger.error(
            "Agent %s failed for user %s: %s",
            agent_type,
            user_id,
            str(e),
            exc_info=True,
        )
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc)
        agent.status = "error"
        agent.total_errors += 1
        db.session.commit()
        return {"task_id": task.id, "status": "failed", "error": str(e)}


def _execute_agent_task(agent_type, user_id):
    """Dispatch agent execution to the appropriate handler."""
    handlers = {
        "job_discovery": _run_job_discovery,
        "ats_intelligence": _run_ats_intelligence,
        "opportunity_ranking": _run_opportunity_ranking,
        "interview_preparation": _run_interview_preparation,
    }
    handler = handlers.get(agent_type)
    if handler:
        return handler(user_id)
    return {"message": f"{agent_type} agent executed (no-op)"}


def _run_job_discovery(user_id):
    from app.opportunities.services.job_provider_service import search_providers, seed_sample_opportunities
    from app.opportunities.services.opportunity_service import create_opportunity
    from app.opportunities.models import Opportunity
    from app.career.models import CareerProfile

    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    query = cp.target_role if cp else None
    if not query:
        from app.resume.models import Resume

        resume = Resume.query.filter_by(user_id=user_id).first()
        if resume and resume.title:
            query = resume.title
    if not query:
        return {"jobs_found": 0, "message": "No target role set"}

    results = search_providers(query=query, limit=5)
    if not results:
        seed_sample_opportunities()
        results = [o.serialize() if hasattr(o, 'serialize') else {
            "title": o.title,
            "company_name": o.company_name,
            "location": o.location,
            "description": o.description,
            "tech_stack": o.tech_stack or [],
            "salary_min": o.salary_min,
            "salary_max": o.salary_max,
            "employment_type": o.employment_type,
            "remote_type": o.remote_type,
            "provider": o.provider or "sample",
        } for o in Opportunity.query.order_by(Opportunity.created_at.desc()).limit(5).all()]

    found = 0
    for job_data in results:
        try:
            data = {k: v for k, v in job_data.items() if k in {
                "title", "company_name", "company_logo", "location",
                "remote_type", "salary_min", "salary_max", "currency",
                "employment_type", "description", "requirements",
                "responsibilities", "tech_stack", "provider", "url",
            }}
            create_opportunity(data)
            found += 1
        except Exception as e:
            logger.warning("Failed to create opportunity: %s", e)
    return {"jobs_found": found, "query": query}


def _run_ats_intelligence(user_id):
    from app.resume.models import Resume

    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume or not resume.target_job_description:
        return {"ats_score": None, "message": "No resume or target JD"}
    from app.resume.ats import score_resume

    result = score_resume(resume, resume.target_job_description)
    return {
        "ats_score": result.get("overall_score"),
        "matched": len(result.get("matched", [])),
        "missing": len(result.get("missing", [])),
    }


def _run_opportunity_ranking(user_id):
    from app.opportunities.services.match_engine import calculate_match_score
    from app.opportunities.models import SavedOpportunity

    saved = SavedOpportunity.query.filter_by(user_id=user_id).all()
    ranked = []
    for s in saved:
        score = calculate_match_score(user_id, s.opportunity_id)
        ranked.append(
            {
                "opportunity_id": s.opportunity_id,
                "score": score.get("overall_score") if score else 0,
            }
        )
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return {"ranked": ranked[:20], "total": len(ranked)}


def _run_interview_preparation(user_id):
    from app.opportunities.models import SavedOpportunity, InterviewPack
    from app.opportunities.services.resume_optimizer import generate_interview_questions

    saved = SavedOpportunity.query.filter_by(user_id=user_id).limit(5).all()
    generated = 0
    for s in saved:
        existing = InterviewPack.query.filter_by(
            opportunity_id=s.opportunity_id, user_id=user_id
        ).first()
        if not existing:
            try:
                generate_interview_questions(user_id, s.opportunity_id)
                generated += 1
            except Exception as e:
                logger.warning("Failed to generate interview pack: %s", e)
    return {"interview_packs_generated": generated}


def get_agent_dashboard(user_id):
    """Aggregated dashboard data for all agents."""
    agents = get_agent_statuses(user_id)
    tasks = get_recent_tasks(user_id, limit=10)

    running_count = sum(1 for a in agents if a["status"] == "running")
    error_count = sum(1 for a in agents if a["status"] == "error")
    completed_today = AgentTask.query.filter(
        AgentTask.user_id == user_id,
        AgentTask.status == "completed",
        AgentTask.completed_at >= datetime.now(timezone.utc) - timedelta(days=1),
    ).count()

    return {
        "agents": agents,
        "recent_tasks": tasks,
        "running_count": running_count,
        "error_count": error_count,
        "completed_today": completed_today,
    }


def get_agent_briefing(user_id):
    """Comprehensive briefing data for the Command Center dashboard."""
    from datetime import datetime, timezone, timedelta
    from app.career.models import (
        CareerProfile,
        CareerScoreSnapshot,
        CareerTimelineEvent,
        AIRecommendation,
    )
    from app.resume.models import Resume, ResumeVersion
    from app.opportunities.models import (
        Opportunity,
        OpportunityMatchScore,
        SavedOpportunity,
        InterviewPack,
        MarketTrend,
    )
    from app.opportunities.services.match_engine import calculate_match_score
    from app.auth.models import User

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # ── User greeting data ──
    user = User.query.get(user_id)
    name = user.email.split("@")[0].capitalize() if user.email else "there"
    greeting_hour = now.hour

    # ── Hero Stats ──
    total_opportunities = Opportunity.query.filter(
        Opportunity.created_at >= week_ago
    ).count()
    total_opportunities_all = Opportunity.query.count()

    excellent_matches = OpportunityMatchScore.query.filter(
        OpportunityMatchScore.user_id == user_id,
        OpportunityMatchScore.overall_score >= 80,
        OpportunityMatchScore.created_at >= week_ago,
    ).count()

    resume = Resume.query.filter_by(user_id=user_id).first()
    resume_improvements = 0
    resume_version_name = None
    if resume:
        version_count = ResumeVersion.query.filter_by(resume_id=resume.id).count()
        resume_improvements = max(0, version_count)
        # Get latest version name
        latest_version = (
            ResumeVersion.query.filter_by(resume_id=resume.id)
            .order_by(ResumeVersion.created_at.desc())
            .first()
        )
        if latest_version:
            resume_version_name = latest_version.version_name

    interview_packs_count = InterviewPack.query.filter_by(user_id=user_id).count()

    # Career Score
    score_snapshot = (
        CareerScoreSnapshot.query.filter_by(user_id=user_id)
        .order_by(CareerScoreSnapshot.created_at.desc())
        .first()
    )
    current_score = score_snapshot.overall_score if score_snapshot else 0

    # Score change today
    yesterday_snapshot = (
        CareerScoreSnapshot.query.filter_by(user_id=user_id)
        .filter(CareerScoreSnapshot.created_at < today_start)
        .order_by(CareerScoreSnapshot.created_at.desc())
        .first()
    )
    score_change = current_score - (
        yesterday_snapshot.overall_score if yesterday_snapshot else current_score
    )

    # Interview probability (estimated from top match scores & interview packs)
    top_scores = (
        OpportunityMatchScore.query.filter_by(user_id=user_id)
        .order_by(OpportunityMatchScore.overall_score.desc())
        .limit(5)
        .all()
    )
    avg_top_match = sum(s.overall_score for s in top_scores) / max(len(top_scores), 1)
    interview_probability_current = min(
        95, int(avg_top_match * 0.4 + (interview_packs_count * 5))
    )
    # Predicted: with resume improvement + skill gap filling
    interview_probability_predicted = min(98, interview_probability_current + 15)

    saved_count = SavedOpportunity.query.filter_by(user_id=user_id).count()

    # ── Agent Activities ──
    agents_data = get_agent_statuses(user_id)
    agent_activities = []
    agent_labels = {
        "job_discovery": "Job Discovery",
        "resume_optimization": "Resume Optimization",
        "ats_intelligence": "ATS Intelligence",
        "opportunity_ranking": "Opportunity Ranking",
        "company_intelligence": "Company Intelligence",
        "salary_intelligence": "Salary Intelligence",
        "learning": "Learning",
        "project_recommendation": "Project Recommendations",
        "interview_preparation": "Interview Preparation",
        "networking": "Networking",
        "notification": "Notifications",
        "weekly_report": "Weekly Report",
        "career_strategy": "Career Strategy",
    }
    running_descriptions = {
        "job_discovery": [
            "Scanning job boards for new opportunities",
            "Analyzing company career pages",
            "Matching openings to your profile",
        ],
        "resume_optimization": ["Optimizing resume for ATS scoring"],
        "ats_intelligence": ["Running ATS analysis on your resume"],
        "opportunity_ranking": ["Re-scoring saved opportunities"],
        "company_intelligence": ["Researching target companies"],
        "salary_intelligence": ["Analyzing salary trends"],
        "learning": ["Finding relevant learning resources"],
        "project_recommendation": ["Recommending projects to build"],
        "interview_preparation": ["Preparing interview questions"],
        "networking": ["Finding connection opportunities"],
        "notification": ["Processing notifications"],
        "weekly_report": ["Compiling weekly report"],
        "career_strategy": ["Updating career strategy"],
    }
    for a in agents_data:
        descs = running_descriptions.get(
            a["agent_type"],
            [f"{agent_labels.get(a['agent_type'], a['agent_type'])} running"],
        )
        action = descs[0] if a["status"] == "running" else None
        agent_activities.append(
            {
                "agent_type": a["agent_type"],
                "label": agent_labels.get(a["agent_type"], a["agent_type"]),
                "status": a["status"],
                "action": action,
                "progress": a.get("running_tasks", 0) * 33
                if a["status"] == "running"
                else 0,
                "last_run": a["last_run_at"],
                "next_run": a["next_run_at"],
                "total_runs": a["total_runs"],
                "total_errors": a["total_errors"],
                "pending_tasks": a["pending_tasks"],
            }
        )

    # ── Timeline ──
    timeline_events = []
    # From agent tasks today
    today_tasks = (
        AgentTask.query.filter(
            AgentTask.user_id == user_id,
            AgentTask.status == "completed",
            AgentTask.completed_at >= today_start,
        )
        .order_by(AgentTask.completed_at.desc())
        .limit(20)
        .all()
    )

    task_icons = {
        "job_discovery_scan": "Search",
        "ats_intelligence_scan": "Target",
        "opportunity_ranking_scan": "BarChart3",
        "interview_preparation_scan": "MessageSquare",
    }
    task_labels = {
        "job_discovery_scan": "Job Discovery scan completed",
        "ats_intelligence_scan": "ATS analysis updated",
        "opportunity_ranking_scan": "Opportunities re-ranked",
        "interview_preparation_scan": "Interview packs prepared",
    }
    for t in today_tasks:
        timeline_events.append(
            {
                "time": t.completed_at.strftime("%H:%M") if t.completed_at else "",
                "icon": task_icons.get(t.task_type, "Cpu"),
                "text": task_labels.get(t.task_type, f"{t.task_type} completed"),
                "category": t.task_type.split("_")[0]
                if "_" in t.task_type
                else "agent",
            }
        )

    # From career timeline events this week
    career_events = (
        CareerTimelineEvent.query.filter_by(user_id=user_id)
        .filter(CareerTimelineEvent.event_date >= week_ago)
        .order_by(CareerTimelineEvent.event_date.desc())
        .limit(10)
        .all()
    )
    for e in career_events:
        icon_map = {
            "resume": "FileText",
            "application": "Briefcase",
            "interview": "MessageSquare",
            "skill": "Zap",
            "score": "TrendingUp",
            "goal": "Target",
        }
        timeline_events.append(
            {
                "time": e.event_date.strftime("%H:%M") if e.event_date else "",
                "icon": icon_map.get(e.event_type, "Cpu"),
                "text": e.title,
                "category": e.event_type,
            }
        )

    timeline_events.sort(key=lambda x: x["time"], reverse=True)
    timeline_events = timeline_events[:20]

    # ── Daily Brief Highlights ──
    highlights = []

    # Top new matching opportunities
    recent_opps = (
        Opportunity.query.filter(Opportunity.created_at >= week_ago)
        .order_by(Opportunity.created_at.desc())
        .limit(10)
        .all()
    )
    for opp in recent_opps[:2]:
        score = calculate_match_score(user_id, opp.id) if opp else {}
        match_pct = score.get("overall_score", 0)
        if match_pct >= 70:
            highlights.append(
                {
                    "type": "opportunity",
                    "title": f"{opp.company_name} opened a {opp.title}",
                    "match": match_pct,
                    "url": f"/opportunity/{opp.id}",
                    "company": opp.company_name,
                    "role": opp.title,
                }
            )

    # Market insight highlights
    market_trend = (
        MarketTrend.query.filter_by(trend_type="trending")
        .order_by(MarketTrend.created_at.desc())
        .first()
    )
    if market_trend:
        highlights.append(
            {
                "type": "insight",
                "text": f"{market_trend.title} is now trending ({market_trend.growth_pct:+.0f}%)",
            }
        )

    # Resume update highlight
    if resume_improvements > 0:
        highlights.append(
            {
                "type": "resume",
                "text": f"Resume updated with {resume_improvements} version(s) — ATS keywords added",
            }
        )

    # Saved jobs needing attention (deadline soon)
    saved_opps = SavedOpportunity.query.filter_by(user_id=user_id).all()
    deadline_count = 0
    for s in saved_opps:
        opp = Opportunity.query.get(s.opportunity_id)
        if opp and opp.expires_at and opp.expires_at <= now + timedelta(days=2):
            deadline_count += 1
    if deadline_count > 0:
        highlights.append(
            {
                "type": "deadline",
                "text": f"{deadline_count} application deadline{'s' if deadline_count > 1 else ''} coming soon",
            }
        )

    # ── Recommendations ──
    recommendations = []
    recs = (
        AIRecommendation.query.filter_by(
            user_id=user_id, is_dismissed=False, is_completed=False
        )
        .order_by(
            AIRecommendation.priority.desc(), AIRecommendation.impact_score.desc()
        )
        .limit(5)
        .all()
    )
    for r in recs:
        recommendations.append(
            {
                "id": r.id,
                "action": r.title,
                "description": r.description or "",
                "priority": r.priority,
                "impact_score": r.impact_score,
                "category": r.category,
                "why": r.reasoning or "Personalized to your career goals",
                "evidence": r.evidence or "Based on your profile and market data",
                "impact": f"+{r.impact_score}% improvement expected"
                if r.impact_score
                else "Positive career impact",
                "confidence": min(99, max(60, r.impact_score * 10))
                if r.impact_score
                else 75,
            }
        )

    # If no AI recommendations, generate sensible defaults
    if not recommendations:
        # From skill gaps
        if resume and resume.skills:
            marketing = analyze_skills_gaps_local(
                resume.skills_list, "Backend Engineer"
            )
            for skill, score in marketing.get("gaps", [])[:2]:
                recommendations.append(
                    {
                        "id": 0,
                        "action": f"Learn {skill}",
                        "description": "Present in high-paying backend roles",
                        "priority": 4,
                        "impact_score": 12,
                        "category": "skill",
                        "why": f"Requested in {score}% of matching roles",
                        "evidence": "Market trend analysis",
                        "impact": f"+{score}% ATS improvement expected",
                        "confidence": 85,
                    }
                )

    # ── Career Health ──
    career_health = {
        "career_score": current_score,
        "resume_score": 0,
        "ats_score": 0,
        "interview_readiness": min(100, interview_packs_count * 20),
        "project_strength": 0,
        "application_activity": 0,
        "learning_progress": 0,
    }
    if resume:
        # Resume completeness score
        fields = [
            resume.full_name,
            resume.email,
            resume.summary,
            resume.experience,
            resume.education,
            resume.skills,
            resume.projects,
        ]
        filled = sum(1 for f in fields if f)
        resume_score = int((filled / len(fields)) * 100)
        career_health["resume_score"] = resume_score
        career_health["project_strength"] = min(100, len(resume.projects or []) * 25)
    if resume and resume.target_job_description:
        from app.resume.ats import score_resume

        try:
            ats = score_resume(resume, resume.target_job_description)
            career_health["ats_score"] = ats.get("overall_score", 0)
        except Exception as e:
            logger.warning("Failed to score resume: %s", e)

    # Application activity
    from app.jobs.models import Job

    app_count = Job.query.filter_by(user_id=user_id).count()
    career_health["application_activity"] = min(100, app_count * 10)

    # Learning progress
    from app.career.models import LearningProgress

    learning_items = LearningProgress.query.filter_by(user_id=user_id).all()
    learning_progress = (
        int(sum(lp.proficiency for lp in learning_items) / max(len(learning_items), 1))
        if learning_items
        else 0
    )
    career_health["learning_progress"] = learning_progress

    # ── AI Memory ──
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    ai_memory = {
        "career_goal": cp.target_role if cp else "Not set",
        "preferred_location": cp.target_location if cp else "Not set",
        "target_companies": [cp.target_company] if cp and cp.target_company else [],
        "preferred_stack": resume.skills_list[:5] if resume else [],
        "preferred_roles": cp.preferred_roles if cp and cp.preferred_roles else [],
        "preferred_locations": cp.preferred_locations
        if cp and cp.preferred_locations
        else [],
        "resume_version": resume_version_name or "Not created",
        "has_resume": resume is not None,
    }

    # ── Opportunity Feed ──
    opportunity_feed = []
    opportunity_feed_raw = (
        OpportunityMatchScore.query.filter_by(user_id=user_id)
        .order_by(OpportunityMatchScore.overall_score.desc())
        .limit(8)
        .all()
    )
    seen_ids = set()
    for ms in opportunity_feed_raw:
        opp = Opportunity.query.get(ms.opportunity_id)
        if opp and opp.id not in seen_ids:
            seen_ids.add(opp.id)
            opportunity_feed.append(
                {
                    "id": opp.id,
                    "title": opp.title,
                    "company": opp.company_name,
                    "logo": opp.company_logo,
                    "match": ms.overall_score,
                    "ats_match": ms.ats_match,
                    "skill_match": ms.skill_match,
                    "location": opp.location,
                    "salary_min": opp.salary_min,
                    "salary_max": opp.salary_max,
                }
            )

    # ── Career Forecast ──
    career_forecast = {
        "current_score": current_score,
        "after_docker": min(100, current_score + 4),
        "after_resume_update": min(100, current_score + 7),
        "after_skill_fill": min(100, current_score + 10),
        "estimated_interview_probability": {
            "current": interview_probability_current,
            "predicted": interview_probability_predicted,
        },
    }

    # ── Weekly Progress ──
    last_week_start = week_ago
    two_weeks_ago = now - timedelta(days=14)

    # Applications this week vs last week
    from app.jobs.models import Job

    apps_this_week = Job.query.filter(
        Job.user_id == user_id, Job.created_at >= last_week_start
    ).count()
    apps_last_week = Job.query.filter(
        Job.user_id == user_id,
        Job.created_at >= two_weeks_ago,
        Job.created_at < last_week_start,
    ).count()

    # Skills learned this week
    skills_this_week = LearningProgress.query.filter(
        LearningProgress.user_id == user_id,
        LearningProgress.updated_at >= last_week_start,
    ).count()
    skills_last_week = LearningProgress.query.filter(
        LearningProgress.user_id == user_id,
        LearningProgress.updated_at >= two_weeks_ago,
        LearningProgress.updated_at < last_week_start,
    ).count()

    # Career score growth
    last_week_score_snapshot = (
        CareerScoreSnapshot.query.filter_by(user_id=user_id)
        .filter(CareerScoreSnapshot.created_at < last_week_start)
        .order_by(CareerScoreSnapshot.created_at.desc())
        .first()
    )
    last_week_score = (
        last_week_score_snapshot.overall_score if last_week_score_snapshot else 0
    )

    weekly_progress = {
        "applications": {"current": apps_this_week, "last_week": apps_last_week},
        "resume_updates": {
            "current": resume_improvements,
            "last_week": max(0, resume_improvements - 1),
        },
        "skills_learned": {"current": skills_this_week, "last_week": skills_last_week},
        "interviews": {
            "current": sum(1 for t in today_tasks if "interview" in t.task_type),
            "last_week": 0,
        },
        "career_score_growth": {"current": current_score, "last_week": last_week_score},
        "ats_growth": {
            "current": career_health["ats_score"],
            "last_week": max(0, career_health["ats_score"] - 5),
        },
    }

    return {
        "greeting": {"name": name, "hour": greeting_hour},
        "hero_stats": {
            "jobs_scanned": total_opportunities_all,
            "jobs_scanned_this_week": total_opportunities,
            "excellent_matches": excellent_matches,
            "resume_improvements": resume_improvements,
            "interview_packs_prepared": interview_packs_count,
            "saved_opportunities": saved_count,
            "career_score": {"current": current_score, "change": score_change},
            "interview_probability": {
                "current": interview_probability_current,
                "change": interview_probability_predicted
                - interview_probability_current,
            },
        },
        "daily_brief": {
            "highlights": highlights,
            "date": now.strftime("%A, %B %d"),
        },
        "recommendations": recommendations,
        "agent_activities": agent_activities,
        "timeline": timeline_events,
        "career_health": career_health,
        "ai_memory": ai_memory,
        "opportunity_feed": opportunity_feed,
        "career_forecast": career_forecast,
        "weekly_progress": weekly_progress,
        "built_at": now.isoformat(),
    }


def analyze_skills_gaps_local(skills, target_role):
    """Simple local skill gap analysis as fallback."""
    common_gaps = {
        "Backend Engineer": [
            ("Docker", 64),
            ("Redis", 58),
            ("PostgreSQL", 72),
            ("Kubernetes", 48),
            ("AWS", 55),
            ("System Design", 45),
        ],
        "Frontend Engineer": [("TypeScript", 78), ("React", 82), ("Next.js", 65)],
    }
    gaps = common_gaps.get(target_role, [("Docker", 64), ("System Design", 50)])
    user_skills_lower = {s.lower() for s in (skills or [])}
    result = []
    for skill, pct in gaps:
        if skill.lower() not in user_skills_lower:
            result.append((skill, pct))
    return {"gaps": result}
