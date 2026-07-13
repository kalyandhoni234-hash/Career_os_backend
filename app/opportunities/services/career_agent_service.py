import logging
from datetime import datetime, timezone
from typing import Optional

from app.extensions import db
from app.opportunities.models import (
    Opportunity,
    SavedOpportunity,
    OpportunityMatchScore,
    OpportunitySkillGap,
)
from app.career.services import build_career_memory
from app.relationships.services import get_due_follow_ups
from app.ai_service import generate_text

logger = logging.getLogger(__name__)


def generate_prioritized_actions(user_id: int, opportunity_id: Optional[int] = None) -> dict:
    memory = build_career_memory(user_id)
    now = datetime.now(timezone.utc)

    saved = (
        SavedOpportunity.query.filter_by(user_id=user_id)
        .order_by(SavedOpportunity.created_at.desc())
        .all()
    )
    scores = (
        OpportunityMatchScore.query.filter_by(user_id=user_id)
        .all()
    )
    score_map = {s.opportunity_id: s for s in scores}

    tasks = []
    reasons = []

    # Upcoming interviews -> highest priority
    interview_records = []
    for s in saved:
        opp = Opportunity.query.get(s.opportunity_id)
        if not opp:
            continue
        stage = s.application_status or "saved"

        if stage == "interview":
            days_until = 0
            tasks.append({
                "priority": "critical",
                "action": f"Prepare for {opp.title} interview at {opp.company_name}",
                "category": "interview",
                "estimated_time_minutes": 45,
                "impact": "very_high",
                "deadline": "Tomorrow" if days_until <= 1 else f"In {days_until} days",
                "reason": f"Interview scheduled with {opp.company_name}.",
                "opportunity_id": opp.id,
            })
            reasons.append(
                f"Interview preparation for {opp.company_name} has the highest "
                f"immediate impact on your application success."
            )

        elif stage == "saved" and not s.applied_at:
            match = score_map.get(opp.id)
            score_val = match.overall_score if match else 0
            if score_val >= 70:
                days_saved = (now - s.created_at).days if s.created_at else 0
                if days_saved >= 7:
                    tasks.append({
                        "priority": "high",
                        "action": f"Apply to {opp.title} at {opp.company_name}",
                        "category": "apply",
                        "estimated_time_minutes": 20,
                        "impact": "high",
                        "deadline": "ASAP" if days_saved >= 14 else "This week",
                        "reason": (
                            f"Strong match ({score_val}%) and saved for "
                            f"{days_saved} days without action."
                        ),
                        "opportunity_id": opp.id,
                    })
                    reasons.append(
                        f"You have a {score_val}% match with {opp.company_name} "
                        f"but haven't applied yet after {days_saved} days."
                    )

        elif stage == "applied" and s.applied_at:
            days_since = (now - s.applied_at).days if s.applied_at else 0
            if days_since >= 7 and days_since <= 30:
                tasks.append({
                    "priority": "medium",
                    "action": f"Follow up on {opp.company_name} application",
                    "category": "follow_up",
                    "estimated_time_minutes": 10,
                    "impact": "medium",
                    "deadline": "This week",
                    "reason": f"No activity for {days_since} days since applying.",
                    "opportunity_id": opp.id,
                })

    # Due follow-ups from networking
    try:
        due_contacts = get_due_follow_ups(user_id)
        for c in due_contacts[:3]:
            tasks.append({
                "priority": "medium",
                "action": f"Contact {c['name']} ({c.get('role', '')} at {c.get('company', '')})",
                "category": "networking",
                "estimated_time_minutes": 10,
                "impact": "medium",
                "deadline": "Today",
                "reason": "Follow-up is overdue.",
                "contact_id": c["id"],
            })
    except Exception:
        pass

    # Resume recomputation if recently changed
    resume = memory.get("resume", {})
    if resume and resume.get("updated_at"):
        days_since = (now - datetime.fromisoformat(resume["updated_at"])).days if resume.get("updated_at") else 99
        if days_since < 7:
            stale_matches = 0
            for s in saved:
                m = score_map.get(s.opportunity_id)
                if m and (now - m.created_at).days > days_since:
                    stale_matches += 1
            if stale_matches > 0:
                tasks.append({
                    "priority": "medium",
                    "action": f"Recompute match scores ({stale_matches} jobs affected)",
                    "category": "maintenance",
                    "estimated_time_minutes": 5,
                    "impact": "high",
                    "deadline": "Today",
                    "reason": (
                        "Your resume was recently updated. Match scores for "
                        f"{stale_matches} saved jobs may be outdated."
                    ),
                })
                reasons.append(
                    "Your resume was updated recently. Match scores should be "
                    "recomputed for accurate comparisons."
                )

    # Skill gap learning
    gaps = (
        OpportunitySkillGap.query.filter_by(user_id=user_id)
        .filter(OpportunitySkillGap.priority == "high")
        .order_by(OpportunitySkillGap.coverage_pct.asc())
        .limit(3)
        .all()
    )
    for gap in gaps:
        missing = (gap.missing_skills or [])[:2]
        for skill in missing:
            tasks.append({
                "priority": "low" if len(tasks) > 5 else "medium",
                "action": f"Learn {skill}",
                "category": "learning",
                "estimated_time_minutes": 30,
                "impact": "high",
                "deadline": "This week",
                "reason": (
                    f"{skill} appears in multiple saved jobs and is missing "
                    f"from your profile."
                ),
                "opportunity_id": gap.opportunity_id,
            })
            reasons.append(
                f"Learning {skill} would increase your eligibility for "
                f"multiple saved opportunities."
            )

    # Sort: critical > high > medium > low
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tasks.sort(key=lambda t: (priority_order.get(t["priority"], 99), t.get("deadline", "")))

    # Top recommendation
    top = tasks[0] if tasks else None

    # If no tasks, check if the user has any saved jobs at all
    if not tasks and not saved:
        return {
            "top_recommendation": None,
            "tasks": [],
            "reasoning": [],
            "message": "Save your first job to get started with personalized recommendations.",
        }

    return {
        "top_recommendation": top,
        "tasks": tasks[:7],
        "reasoning": reasons[:3],
        "message": top["reason"] if top else None,
    }


def generate_ai_career_advice(user_id: int, opportunity_id: int) -> dict:
    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return {"advice": None, "error": "Opportunity not found"}

    saved = SavedOpportunity.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    match = OpportunityMatchScore.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    gaps = OpportunitySkillGap.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()

    match_score = match.overall_score if match else 0
    missing = (gaps.missing_skills or []) if gaps else []
    stage = (saved.application_status or "saved") if saved else "saved"

    system_instruction = (
        "You are a senior career advisor AI. Given a user's job application context, "
        "generate a single, specific, actionable recommendation. "
        "Return ONLY valid JSON with no markdown:\n"
        '{"action":"...","reason":"...","estimated_impact":"low|medium|high|very_high",'
        '"estimated_time_minutes":30,"category":"interview|apply|learning|networking|resume"}'
    )

    prompt = (
        f"Job: {opp.title} at {opp.company_name}\n"
        f"Stage: {stage}\n"
        f"Match Score: {match_score}%\n"
        f"Missing Skills: {', '.join(missing[:5]) or 'none'}\n"
        f"Tech Stack: {', '.join(opp.tech_stack or [])}\n"
        f"Application Status: {stage}\n\n"
        f"Generate one specific action this user should take right now."
    )

    try:
        import json
        import re
        raw = generate_text(prompt, model="gemini", system_instruction=system_instruction)
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        advice = json.loads(cleaned)
    except Exception as e:
        logger.warning("AI advice generation failed: %s", e)
        advice = _fallback_advice(match_score, stage, missing)

    return {"advice": advice}


def _fallback_advice(match_score: int, stage: str, missing: list[str]) -> dict:
    if stage == "interview":
        return {
            "action": "Review the interview preparation pack for this role",
            "reason": "Your interview is upcoming or in progress.",
            "estimated_impact": "very_high",
            "estimated_time_minutes": 45,
            "category": "interview",
        }
    if stage == "saved" and match_score >= 70:
        return {
            "action": "Submit your application for this role",
            "reason": f"You have a strong {match_score}% match. Don't wait too long.",
            "estimated_impact": "high",
            "estimated_time_minutes": 20,
            "category": "apply",
        }
    if missing:
        return {
            "action": f"Start learning {missing[0]}",
            "reason": f"{missing[0]} is required for this role and missing from your profile.",
            "estimated_impact": "high",
            "estimated_time_minutes": 30,
            "category": "learning",
        }
    return {
        "action": "Complete your profile to get better match scores",
        "reason": "A complete profile helps the AI generate better recommendations.",
        "estimated_impact": "medium",
        "estimated_time_minutes": 15,
        "category": "resume",
    }
