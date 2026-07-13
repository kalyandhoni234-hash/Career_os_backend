import logging
from datetime import datetime, timezone

from app.extensions import db
from app.opportunities.models import (
    Opportunity,
    SavedOpportunity,
    OpportunityMatchScore,
    OpportunitySkillGap,
)
from app.resume.models import Resume
from app.relationships.models import Contact

logger = logging.getLogger(__name__)


def compute_application_health(user_id: int, opportunity_id: int) -> dict:
    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return {"error": "Opportunity not found"}

    saved = SavedOpportunity.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    match = OpportunityMatchScore.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    gaps = OpportunitySkillGap.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    contacts = Contact.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).count()
    resume = Resume.query.filter_by(user_id=user_id).first()

    factors = {}

    # 1. Resume Quality (25%)
    resume_score = 0
    resume_reasons = []
    if resume:
        if resume.summary:
            resume_score += 30
        else:
            resume_reasons.append("Add a professional summary")
        skills_count = len(resume.skills or [])
        resume_score += min(skills_count * 5, 30)
        if skills_count < 5:
            resume_reasons.append("Add more skills to your resume")
        exp_count = len(resume.experience or [])
        resume_score += min(exp_count * 10, 25)
        if exp_count == 0:
            resume_reasons.append("Add work experience to your resume")
        if resume.education:
            resume_score += 15
        else:
            resume_reasons.append("Add education details")
    else:
        resume_reasons.append("Create a resume")
    factors["resume_quality"] = {
        "score": min(resume_score, 100),
        "weight": 25,
        "reasons": resume_reasons,
    }

    # 2. ATS Compatibility (20%)
    ats_score = match.ats_match if match else 0
    ats_reasons = []
    if ats_score < 40:
        ats_reasons.append("Resume keywords need optimization for ATS")
    elif ats_score < 70:
        ats_reasons.append("Moderate ATS compatibility — consider tuning keywords")
    else:
        ats_reasons.append("Good ATS compatibility")
    factors["ats_compatibility"] = {
        "score": ats_score,
        "weight": 20,
        "reasons": ats_reasons,
    }

    # 3. Networking (15%)
    networking_score = min(contacts * 20, 100)
    networking_reasons = []
    if contacts == 0:
        networking_reasons.append("No contacts linked — connect with people at this company")
    elif contacts < 3:
        networking_reasons.append(f"You have {contacts} contact(s) — aim for 3+")
    else:
        networking_reasons.append(f"Good networking ({contacts} contacts)")
    factors["networking"] = {
        "score": networking_score,
        "weight": 15,
        "reasons": networking_reasons,
    }

    # 4. Company Research (10%)
    company_info_score = 0
    company_reasons = []
    if opp.company_name:
        company_info_score += 30
    if opp.description:
        company_info_score += 30
    if opp.tech_stack:
        company_info_score += 20
    if opp.location:
        company_info_score += 20
    company_reasons.append("Company information available" if company_info_score >= 60 else "Limited company information")
    factors["company_research"] = {
        "score": company_info_score,
        "weight": 10,
        "reasons": company_reasons,
    }

    # 5. Interview Readiness (15%)
    interview_score = 0
    interview_reasons = []
    stage = saved.application_status if saved else "saved"
    if stage == "interview":
        interview_score = max(0, min(100 - (gaps.coverage_pct if gaps else 0), 100))
        interview_reasons.append("Prepare for scheduled interview")
    elif stage == "applied":
        interview_score = 50
        interview_reasons.append("Application submitted — start interview preparation early")
    elif stage == "saved":
        interview_score = 30
        interview_reasons.append("Not yet applied — focus on application first")
    else:
        interview_score = 60
        interview_reasons.append("Maintain readiness")
    factors["interview_readiness"] = {
        "score": interview_score,
        "weight": 15,
        "reasons": interview_reasons,
    }

    # 6. Follow-up Status (10%)
    follow_up_score = 0
    follow_up_reasons = []
    now = datetime.now(timezone.utc)
    if saved and saved.applied_at:
        days_since = (now - saved.applied_at).days
        if days_since < 3:
            follow_up_score = 80
            follow_up_reasons.append("Recently applied — wait before following up")
        elif days_since < 7:
            follow_up_score = 60
            follow_up_reasons.append("Good time to prepare while waiting")
        elif days_since < 14:
            follow_up_score = 40
            follow_up_reasons.append("Consider a polite follow-up email")
        else:
            follow_up_score = 20
            follow_up_reasons.append("Follow-up is overdue")
    else:
        follow_up_score = 0
        follow_up_reasons.append("Not yet applied")
    factors["follow_up_status"] = {
        "score": follow_up_score,
        "weight": 10,
        "reasons": follow_up_reasons,
    }

    # 7. Documentation (5%)
    doc_score = 0
    doc_reasons = []
    if saved and saved.notes:
        doc_score += 50
        doc_reasons.append("Notes recorded")
    else:
        doc_reasons.append("Add notes for this application")
    if opp.requirements:
        doc_score += 25
    if opp.responsibilities:
        doc_score += 25
    factors["documentation"] = {
        "score": doc_score,
        "weight": 5,
        "reasons": doc_reasons,
    }

    overall = sum(
        f["score"] * f["weight"] / 100 for f in factors.values()
    )
    overall = round(overall)

    all_reasons = []
    for f in factors.values():
        all_reasons.extend(f["reasons"])

    return {
        "overall_score": overall,
        "factors": factors,
        "top_improvements": [
            r for r in all_reasons
            if any(kw in r.lower() for kw in ["add", "no", "limited", "consider", "aim", "create", "not"])
        ][:5],
        "summary": _health_summary(overall),
    }


def _health_summary(score: int) -> str:
    if score >= 80:
        return "Strong application — you're well-prepared"
    if score >= 60:
        return "Good foundation — address the improvement areas below"
    if score >= 40:
        return "Needs work — focus on the key gaps identified"
    return "Early stage — start building the fundamentals"


def compute_health_for_all_saved(user_id: int) -> list[dict]:
    saved = SavedOpportunity.query.filter_by(user_id=user_id).all()
    results = []
    for s in saved:
        health = compute_application_health(user_id, s.opportunity_id)
        if "error" not in health:
            results.append({
                "opportunity_id": s.opportunity_id,
                "health_score": health["overall_score"],
                "summary": health["summary"],
            })
    return results
