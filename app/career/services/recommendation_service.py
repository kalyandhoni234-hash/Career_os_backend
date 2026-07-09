from datetime import datetime, timezone
from app.extensions import db
from app.career.models import AIRecommendation
from app.career.services.career_memory_service import build_career_memory


def generate_recommendations(user_id, force=False):
    """Generate context-aware recommendations using AI analysis."""
    from app.ai_service import generate_text
    from app.resume.models import Resume

    memory = build_career_memory(user_id)

    resume = Resume.query.filter_by(user_id=user_id).first()
    has_resume = resume is not None

    # First, clear old non-dismissed/non-completed recs if forcing refresh
    if force:
        old = AIRecommendation.query.filter_by(
            user_id=user_id, is_dismissed=False, is_completed=False
        ).all()
        for r in old:
            r.is_dismissed = True
        db.session.commit()

    # Build context for AI
    context_parts = []
    if memory.get("resume", {}).get("summary"):
        context_parts.append(f"Summary: {memory['resume']['summary'][:200]}")
    skills = memory.get("skills", {}).get("resume_skills", [])
    if skills:
        context_parts.append(f"Skills: {', '.join(skills[:15])}")
    if memory.get("career_profile", {}).get("target_role"):
        cp = memory["career_profile"]
        context_parts.append(f"Target: {cp.get('target_role')} at {cp.get('target_company', 'any company')}")
    missing = memory.get("ats", {}).get("missing_skills", [])
    if missing:
        context_parts.append(f"Missing Skills: {', '.join(missing[:10])}")
    app_data = memory.get("applications", {})
    context_parts.append(f"Applications: {app_data.get('total_applications', 0)} total, {app_data.get('offer_count', 0)} offers")
    goals = memory.get("goals", {}).get("active_goals", [])
    if goals:
        context_parts.append(f"Active Goals: {', '.join(g['title'] for g in goals[:3])}")

    # Only generate AI recs if we have enough context
    if has_resume and (skills or missing):
        context = "\n".join(context_parts)
        prompt = f"""Based on this user's career profile, generate 5-7 personalized recommendations.

User Context:
{context}

For each recommendation provide:
- rec_type: one of: resume, skill, project, job, learning, interview, portfolio, networking, goal
- title: short action title
- description: why this matters and what to do (1-2 sentences)
- priority: 1-5 (5=highest)
- impact_score: 0-100 (estimated ATS/score gain)
- category: the skill or area it relates to
- action_link: relative URL path if applicable (/resume, /jobs, /coach, /roadmaps, etc.)

Return ONLY valid JSON array. No markdown. No explanation.
Example:
[
  {{"rec_type": "learning", "title": "Learn Docker", "description": "Docker is missing from your skills. Adding it could increase your ATS score by ~6%.", "priority": 5, "impact_score": 6, "category": "DevOps", "action_link": "/roadmaps"}}
]"""

        try:
            raw = generate_text(prompt, model="gemini")
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                cleaned = parts[1] if len(parts) > 1 else cleaned
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            import json
            recs_data = json.loads(cleaned)
        except Exception:
            recs_data = _generate_fallback_recs(memory)
    else:
        recs_data = _generate_fallback_recs(memory)

    # Persist recommendations
    saved = []
    for r_data in recs_data:
        rec = AIRecommendation(
            user_id=user_id,
            rec_type=r_data.get("rec_type", "skill"),
            title=r_data.get("title", "Improve your profile"),
            description=r_data.get("description", ""),
            priority=r_data.get("priority", 3),
            impact_score=r_data.get("impact_score", 0),
            category=r_data.get("category", ""),
            action_link=r_data.get("action_link", ""),
        )
        db.session.add(rec)
        db.session.flush()
        saved.append({
            "id": rec.id,
            "rec_type": rec.rec_type,
            "title": rec.title,
            "description": rec.description,
            "priority": rec.priority,
            "impact_score": rec.impact_score,
            "category": rec.category,
            "action_link": rec.action_link,
        })
    db.session.commit()
    return saved


def _generate_fallback_recs(memory):
    """Generate rule-based recommendations when AI is unavailable."""
    recs = []
    skills = memory.get("skills", {}).get("resume_skills", [])
    missing = memory.get("ats", {}).get("missing_skills", [])
    apps = memory.get("applications", {})
    goals = memory.get("goals", {}).get("active_goals", [])

    # Skill-based recommendations
    if missing:
        for skill in missing[:3]:
            recs.append({
                "rec_type": "learning",
                "title": f"Learn {skill}",
                "description": f"{skill} is missing from your skills. Adding it could improve your ATS score.",
                "priority": 4,
                "impact_score": 5,
                "category": "Skill",
                "action_link": "/roadmaps",
            })

    # Application-based
    if apps.get("total_applications", 0) < 5:
        recs.append({
            "rec_type": "job",
            "title": "Apply to more positions",
            "description": "You've only applied to a few positions. Increasing applications improves your chances.",
            "priority": 5,
            "impact_score": 10,
            "category": "Career",
            "action_link": "/jobs",
        })

    # Resume improvements
    if not memory.get("resume", {}).get("summary"):
        recs.append({
            "rec_type": "resume",
            "title": "Add a professional summary",
            "description": "Your resume is missing a summary. A strong summary can increase ATS matching.",
            "priority": 5,
            "impact_score": 8,
            "category": "Resume",
            "action_link": "/resume",
        })

    # Interview prep
    if apps.get("interview_count", 0) > 0 and apps.get("offer_count", 0) == 0:
        recs.append({
            "rec_type": "interview",
            "title": "Practice technical interviews",
            "description": "You've had interviews but no offers yet. Focused interview prep could help convert.",
            "priority": 4,
            "impact_score": 15,
            "category": "Interview",
            "action_link": "/coach",
        })

    # Goal-based
    if not goals:
        recs.append({
            "rec_type": "goal",
            "title": "Set a career goal",
            "description": "Setting a target role helps the AI personalize all recommendations.",
            "priority": 3,
            "impact_score": 5,
            "category": "Career",
            "action_link": "/career-overview",
        })

    # General growth
    if len(skills) < 5:
        recs.append({
            "rec_type": "skill",
            "title": "Expand your skill set",
            "description": "You have fewer than 5 skills listed. Adding more technologies broadens opportunities.",
            "priority": 3,
            "impact_score": 4,
            "category": "Skill",
            "action_link": "/resume",
        })

    return recs


def get_action_center(user_id):
    """Build today's action plan sorted by priority and impact."""
    recs = AIRecommendation.query.filter_by(
        user_id=user_id, is_dismissed=False, is_completed=False
    ).order_by(
        AIRecommendation.priority.desc(),
        AIRecommendation.impact_score.desc(),
    ).all()

    plan = []
    for r in recs:
        plan.append({
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "priority": r.priority,
            "impact_score": r.impact_score,
            "category": r.category,
            "action_link": r.action_link,
            "rec_type": r.rec_type,
            "stars": "★" * r.priority + "☆" * (5 - r.priority),
        })
    return plan
