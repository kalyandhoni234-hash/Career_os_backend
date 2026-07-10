from app.career.services.career_memory_service import build_career_memory


def build_ai_profile(user_id):
    """Build an AI-friendly profile summarizing the user's career state."""
    memory = build_career_memory(user_id)

    resume = memory.get("resume", {})
    cp = memory.get("career_profile", {})
    skills = memory.get("skills", {})
    ats = memory.get("ats", {})
    apps = memory.get("applications", {})
    goals = memory.get("goals", {})
    learning = memory.get("learning", [])

    # Current level
    current_level = cp.get("career_level", "student")
    if resume.get("experience_entries", 0) > 2:
        current_level = "mid-level"
    elif resume.get("experience_entries", 0) > 0:
        current_level = "entry-level"

    # Compute strong vs weak skills
    all_skills = skills.get("resume_skills", [])
    learning_skills = {
        skill_entry["skill"]: skill_entry["proficiency"] for skill_entry in learning
    }
    strong = []
    weak = []

    for s in all_skills:
        prof = learning_skills.get(s.lower(), 0)
        if prof >= 60:
            strong.append(s)
        else:
            weak.append(s)

    # Add missing skills from ATS
    missing = ats.get("missing_skills", [])
    for ms in missing:
        if ms not in weak and ms not in strong:
            weak.append(ms)

    # Determine top recommendation
    top_rec = None
    if weak:
        top_rec = f"Learn {weak[0]}"
    elif not resume.get("summary"):
        top_rec = "Update resume summary"
    elif apps.get("total_applications", 0) < 5:
        top_rec = "Apply to more positions"

    target_role = cp.get("target_role") or resume.get("title") or "Unknown"
    target_company = cp.get("target_company") or "target company"

    return {
        "name": resume.get("full_name") or "User",
        "current_level": current_level,
        "target_role": target_role,
        "target_company": target_company,
        "career_goal_type": cp.get("career_goal_type", "internship"),
        "ats_score": ats.get("overall_score", 0),
        "keyword_match": ats.get("keyword_match", 0),
        "strong_skills": strong[:8],
        "weak_skills": weak[:8],
        "resume_summary_present": bool(resume.get("summary")),
        "total_experience_entries": resume.get("experience_entries", 0),
        "total_projects": resume.get("projects", 0),
        "applications_total": apps.get("total_applications", 0),
        "interview_count": apps.get("interview_count", 0),
        "offer_count": apps.get("offer_count", 0),
        "active_goals": len(goals.get("active_goals", [])),
        "roadmap_count": len(memory.get("roadmaps", [])),
        "top_recommendation": top_rec,
        "missing_ats_skills": missing[:5],
    }
