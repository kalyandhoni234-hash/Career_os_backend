import logging
from datetime import datetime, timezone, date

from app.intelligence.engine import get_unified_profile
from app.career.services.career_score_service import compute_career_score
from app.career.services.roadmap_engine import get_dashboard_roadmap
from app.career.services.recommendation_service import get_action_center
from app.career.services.skill_graph_service import build_skill_graph, analyze_skill_gaps
from app.ai_service import generate_text, sanitize_for_prompt

logger = logging.getLogger(__name__)


def build_context(user_id: int) -> dict:
    profile = get_unified_profile(user_id)
    score = compute_career_score(user_id)
    roadmap = get_dashboard_roadmap(user_id)
    actions = get_action_center(user_id)
    skill_graph = build_skill_graph(user_id)
    target = (
        profile.get("career", {}).get("dream_role")
        or profile.get("career", {}).get("current_role")
    )
    gaps = analyze_skill_gaps(user_id, target_role=target) if target else {}

    return {
        "basic": {
            "name": profile.get("basic", {}).get("full_name", "there"),
            "headline": profile.get("basic", {}).get("headline", ""),
            "location": profile.get("basic", {}).get("location", ""),
        },
        "career": profile.get("career", {}),
        "skills": [s.get("name") for s in profile.get("skills", [])],
        "skill_categories": skill_graph,
        "top_actions": actions[:5] if actions else [],
        "roadmap": roadmap,
        "career_score": score.get("overall_score", 0),
        "score_breakdown": score.get("breakdown", {}),
        "skill_gaps": gaps.get("gaps", []),
        "gap_coverage": gaps.get("coverage", 0),
        "today": date.today().isoformat(),
    }


def _context_summary(context: dict) -> str:
    lines = []
    c = context.get("career", {})
    lines.append(f"Current role: {c.get('current_role', 'Not set')}")
    lines.append(f"Target role: {c.get('dream_role', 'Not set')}")
    lines.append(f"Career level: {c.get('career_level', 'Not set')}")
    lines.append(f"Years experience: {c.get('years_experience', 0)}")

    skills = context.get("skills", [])
    lines.append(f"Skills ({len(skills)}): {', '.join(skills[:15])}{'...' if len(skills) > 15 else ''}")

    gaps = context.get("skill_gaps", [])
    if gaps:
        lines.append(f"Top skill gaps: {', '.join(g.get('skill','') for g in gaps[:5])}")

    score = context.get("career_score", 0)
    lines.append(f"Overall career readiness: {score}/100")

    roadmap = context.get("roadmap")
    if roadmap:
        lines.append(f"Active roadmap: {roadmap.get('title', '')} ({roadmap.get('progress', 0)}% complete, {roadmap.get('estimated_days_remaining', 0)} days remaining)")
        cl = roadmap.get("current_lesson")
        if cl:
            lines.append(f"Current lesson: {cl}")

    actions = context.get("top_actions", [])
    if actions:
        lines.append("Top recommended tasks:")
        for a in actions[:3]:
            lines.append(f"  - [{a.get('priority','')}] {a.get('title','')} ({a.get('impact_score',0)} impact)")

    lines.append(f"\nToday's date: {context.get('today')}")
    return "\n".join(lines)


DAILY_ACTION_PROMPT = """You are a career coach analyzing a user's profile. Based ONLY on the context below, identify the single most impactful action the user should take TODAY to advance their career.

Context:
{context}

Rules:
1. Pick ONE specific, actionable task. If the user has a roadmap, prefer the next incomplete lesson or a directly related task.
2. State the task clearly in 1 sentence.
3. Give a 1-sentence reason explaining why this matters (cite specific context fields like skill gaps, roadmap progress, or career score).
4. Tag impact as "high", "medium", or "low" based on how much this moves their career forward.
5. If no roadmap or actions exist, suggest a foundational first step (e.g. complete your profile, add skills).

Return ONLY valid JSON with exactly these keys:
{{"task": "...", "reason": "...", "impact": "high|medium|low", "based_on": ["skill_gaps", "roadmap", "career_score", "top_actions", "profile_completion"]}}

Only include the context fields you actually used in `based_on`."""


def get_next_action(user_id: int) -> dict:
    context = build_context(user_id)
    summary = _context_summary(context)
    prompt = DAILY_ACTION_PROMPT.format(context=summary)

    try:
        raw = generate_text(prompt, model="gemini")
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        import json
        result = json.loads(cleaned)
        result.setdefault("based_on", [])
        return result
    except Exception as e:
        logger.warning("AI next-action failed, falling back: %s", e)
        return _fallback_next_action(context)


def _fallback_next_action(context: dict) -> dict:
    actions = context.get("top_actions", [])
    if actions:
        a = actions[0]
        return {
            "task": a.get("title", "Review your recommendations"),
            "reason": a.get("description", "Recommended based on your profile"),
            "impact": "high" if a.get("priority", 0) >= 4 else "medium" if a.get("priority", 0) >= 2 else "low",
            "based_on": ["top_actions"],
        }

    roadmap = context.get("roadmap")
    if roadmap:
        cl = roadmap.get("current_lesson")
        if cl:
            return {
                "task": f"Complete '{cl}' in your {roadmap.get('title','')} roadmap",
                "reason": f"You're {roadmap.get('progress',0)}% through your roadmap",
                "impact": "high",
                "based_on": ["roadmap"],
            }

    gaps = context.get("skill_gaps", [])
    if gaps:
        g = gaps[0]
        return {
            "task": f"Start learning {g.get('skill','')}",
            "reason": g.get("reason", "This skill bridges a critical gap"),
            "impact": "medium",
            "based_on": ["skill_gaps"],
        }

    score = context.get("career_score", 0)
    if score < 50:
        return {
            "task": "Complete your career profile",
            "reason": "Your career readiness score is low. Adding profile details unlocks better recommendations.",
            "impact": "high",
            "based_on": ["career_score"],
        }

    return {
        "task": "Explore career paths to set a target role",
        "reason": "Without a target role, recommendations can't be personalized",
        "impact": "medium",
        "based_on": [],
    }
