import logging
from collections import Counter
from datetime import datetime, timezone

from app.extensions import db
from app.opportunities.models import (
    Opportunity,
    SavedOpportunity,
    OpportunityMatchScore,
    ResumeVersionByCompany,
)
from app.knowledge.models import InterviewRecord

logger = logging.getLogger(__name__)


def compute_predictive_analytics(user_id: int) -> dict:
    saved = SavedOpportunity.query.filter_by(user_id=user_id).all()
    ids = [s.opportunity_id for s in saved]
    opportunities = (
        Opportunity.query.filter(Opportunity.id.in_(ids)).all()
        if ids
        else []
    )
    opp_map = {o.id: o for o in opportunities}

    total_apps = len(saved)

    applied = [s for s in saved if s.applied_at]
    interviews = [s for s in saved if s.application_status == "interview"]
    offers = [s for s in saved if s.application_status in ("offer", "accepted")]
    rejected = [s for s in saved if s.application_status == "rejected"]

    interview_rate = round(len(interviews) / max(len(applied), 1) * 100)
    offer_rate = round(len(offers) / max(len(applied), 1) * 100)
    rejection_rate = round(len(rejected) / max(len(applied), 1) * 100)

    # Skill demand
    skill_counter: Counter = Counter()
    for o in opportunities:
        for s in o.tech_stack or []:
            if isinstance(s, str):
                skill_counter[s.strip()] += 1
    total_opps = len(opportunities)
    skill_demand = {
        skill: {
            "count": count,
            "percentage": round(count / max(total_opps, 1) * 100),
        }
        for skill, count in skill_counter.most_common(20)
    }

    # Top skills requested
    most_requested = [
        {"skill": skill, "percentage": info["percentage"]}
        for skill, info in list(skill_demand.items())[:10]
    ]

    # Match score trends
    match_scores = (
        OpportunityMatchScore.query.filter_by(user_id=user_id)
        .order_by(OpportunityMatchScore.created_at.asc())
        .all()
    )
    score_history = [
        {
            "date": m.created_at.isoformat() if m.created_at else "",
            "score": m.overall_score,
            "opportunity_id": m.opportunity_id,
        }
        for m in match_scores
    ]

    avg_resume_match = (
        round(sum(m.overall_score for m in match_scores) / max(len(match_scores), 1))
        if match_scores
        else 0
    )

    # Highest performing resume versions
    resume_versions = (
        ResumeVersionByCompany.query.filter_by(user_id=user_id)
        .order_by(ResumeVersionByCompany.ats_score.desc().nullslast())
        .limit(5)
        .all()
    )
    top_resumes = [
        {
            "company": r.company_name,
            "ats_score": r.ats_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in resume_versions
    ]

    # Interview conversion
    interview_records = InterviewRecord.query.filter_by(user_id=user_id).all()
    total_interviews = len(interview_records)
    offers_from_interviews = sum(1 for r in interview_records if r.offer_received)
    interview_conversion = (
        round(offers_from_interviews / max(total_interviews, 1) * 100)
    )

    # Most common missing skills (from match score explanations)
    missing_skill_counter: Counter = Counter()
    for m in match_scores:
        explanation = m.explanation or {}
        missing_str = explanation.get("missing_skills", "")
        if missing_str and isinstance(missing_str, str):
            for skill in missing_str.split(","):
                skill = skill.strip()
                if skill:
                    missing_skill_counter[skill] += 1
    most_missing = [
        {"skill": skill, "count": count}
        for skill, count in missing_skill_counter.most_common(10)
    ]

    # Companies applied to
    company_counter: Counter = Counter()
    for o in opportunities:
        company_counter[o.company_name] += 1
    top_companies = [
        {"name": name, "count": count}
        for name, count in company_counter.most_common(10)
    ]

    # Monthly application trend
    monthly: Counter = Counter()
    for s in saved:
        if s.created_at:
            month = s.created_at.strftime("%Y-%m")
            monthly[month] += 1
    monthly_trend = [
        {"month": month, "count": count}
        for month, count in sorted(monthly.items())
    ]

    return {
        "summary": {
            "total_applications": total_apps,
            "total_applied": len(applied),
            "total_interviews": total_interviews,
            "total_offers": len(offers),
        },
        "rates": {
            "interview_rate": interview_rate,
            "offer_rate": offer_rate,
            "rejection_rate": rejection_rate,
            "interview_conversion_rate": interview_conversion,
        },
        "scores": {
            "average_resume_match": avg_resume_match,
            "score_history": score_history,
        },
        "skills": {
            "most_requested": most_requested,
            "most_missing": most_missing,
        },
        "top_companies": top_companies,
        "top_resumes": top_resumes,
        "monthly_trend": monthly_trend,
        "recommendations": _generate_recommendations(
            most_requested, most_missing, avg_resume_match
        ),
    }


def _generate_recommendations(
    most_requested: list[dict],
    most_missing: list[dict],
    avg_match: int,
) -> list[dict]:
    recs = []
    requested_skills = {r["skill"] for r in most_requested[:5]}
    missing_skill_names = {m["skill"] for m in most_missing[:5]}
    high_impact_gaps = requested_skills & missing_skill_names

    for skill in high_impact_gaps:
        pct = next(
            (r["percentage"] for r in most_requested if r["skill"] == skill), 0
        )
        recs.append({
            "recommendation": f"Learning {skill} would improve eligibility for ~{pct}% of your opportunities",
            "impact": "high",
            "category": "learning",
        })

    if avg_match < 70:
        recs.append({
            "recommendation": f"Your average resume match is {avg_match}% — consider optimizing your resume for ATS",
            "impact": "high",
            "category": "resume",
        })

    if most_missing:
        recs.append({
            "recommendation": f"Fill skill gaps: {most_missing[0]['skill']} appears in {most_missing[0]['count']} of your saved jobs",
            "impact": "medium",
            "category": "learning",
        })

    return recs
