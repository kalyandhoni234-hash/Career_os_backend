import logging
from collections import Counter

from app.extensions import db
from app.opportunities.models import Opportunity, SavedOpportunity, OpportunitySkillGap

logger = logging.getLogger(__name__)

SKILL_ALIASES = {
    "golang": "Go",
    "nextjs": "Next.js",
    "csharp": "C#",
    "dotnet": ".NET",
    "k8s": "Kubernetes",
    "reactjs": "React",
    "vuejs": "Vue.js",
    "nodejs": "Node.js",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "python": "Python",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "dynamodb": "DynamoDB",
    "elasticsearch": "Elasticsearch",
    "ci/cd": "CI/CD",
    "ml": "Machine Learning",
    "ai": "AI",
    "rest": "REST",
    "restful": "REST",
}


def _normalize_skill(name: str) -> str:
    key = name.strip().lower().replace(".", "").replace(" ", "")
    return SKILL_ALIASES.get(key, name.strip())


def _flatten_tech_stacks(opportunities: list[Opportunity]) -> list[str]:
    skills: list[str] = []
    for opp in opportunities:
        stack = opp.tech_stack or []
        for s in stack:
            if isinstance(s, str) and s.strip():
                skills.append(_normalize_skill(s))
        desc = (opp.description or "") + " " + (" ".join(opp.requirements or []))
        from app.opportunities.services.job_parser import extract_tech_stack

        parsed = extract_tech_stack(desc)
        skills.extend(s.strip() for s in parsed if s.strip())
    return skills


def compute_opportunity_intelligence(user_id: int) -> dict:
    saved_ids = (
        SavedOpportunity.query.filter_by(user_id=user_id)
        .with_entities(SavedOpportunity.opportunity_id)
        .all()
    )
    ids = [row[0] for row in saved_ids]
    if not ids:
        return {"total_jobs": 0, "insights": [], "skill_frequency": {}, "summary": {}}

    opportunities = Opportunity.query.filter(Opportunity.id.in_(ids)).all()

    total = len(opportunities)

    skill_counter: Counter = Counter()
    for opp in opportunities:
        stack = opp.tech_stack or []
        for s in stack:
            if isinstance(s, str) and s.strip():
                skill_counter[_normalize_skill(s)] += 1

    desc_skills = _flatten_tech_stacks(opportunities)
    desc_counter = Counter(desc_skills)
    skill_counter += desc_counter

    skill_frequency = {}
    for skill, count in skill_counter.most_common():
        pct = round((count / total) * 100) if total > 0 else 0
        skill_frequency[skill] = {"count": count, "percentage": pct}

    # Missing skills aggregated across all job-specific gap analyses
    aggregated_missing: Counter = Counter()
    all_gaps = (
        OpportunitySkillGap.query.filter_by(user_id=user_id)
        .filter(OpportunitySkillGap.opportunity_id.in_(ids))
        .all()
    )
    for gap in all_gaps:
        missing = gap.missing_skills or []
        for s in missing:
            if isinstance(s, str) and s.strip():
                aggregated_missing[_normalize_skill(s)] += 1

    # User's current skills (from gap analysis)
    user_skills: set[str] = set()
    for gap in all_gaps:
        current = gap.current_skills or []
        for s in current:
            if isinstance(s, str) and s.strip():
                user_skills.add(_normalize_skill(s))

    recommendations = []
    for skill, freq in skill_frequency.most_common(20):
        if skill.lower() in {s.lower() for s in user_skills}:
            continue
        gain = freq["percentage"]
        if gain >= 30:
            recommendations.append({
                "skill": skill,
                "appears_in_pct": gain,
                "times_required": freq["count"],
                "message": (
                    f"Learning {skill} increases eligibility for "
                    f"approximately {gain}% of your saved jobs."
                ),
                "priority": "high" if gain >= 60 else "medium" if gain >= 30 else "low",
            })

    # Salary distribution
    salaries = []
    for opp in opportunities:
        if opp.salary_min and opp.salary_max:
            salaries.append({
                "min": opp.salary_min,
                "max": opp.salary_max,
                "currency": opp.currency or "INR",
                "title": opp.title,
                "company": opp.company_name,
            })

    salary_avg = None
    if salaries:
        all_mins = [s["min"] for s in salaries if s["min"]]
        all_maxs = [s["max"] for s in salaries if s["max"]]
        if all_mins and all_maxs:
            salary_avg = (sum(all_mins) / len(all_mins) + sum(all_maxs) / len(all_maxs)) / 2

    # Location distribution
    location_counter: Counter = Counter()
    for opp in opportunities:
        if opp.location:
            city = opp.location.split(",")[0].strip()
            location_counter[city] += 1

    # Top companies
    company_counter: Counter = Counter()
    for opp in opportunities:
        company_counter[opp.company_name] += 1

    # Employment type distribution
    emp_type_counter: Counter = Counter()
    for opp in opportunities:
        emp_type_counter[opp.employment_type or "full-time"] += 1

    # Remote/Hybrid/Onsite breakdown
    remote_counter: Counter = Counter()
    for opp in opportunities:
        remote_counter[opp.remote_type or "on-site"] += 1

    # Title analysis
    title_counter: Counter = Counter()
    for opp in opportunities:
        title_counter[opp.title] += 1

    summary = {
        "total_jobs": total,
        "unique_companies": len(company_counter),
        "unique_locations": len(location_counter),
        "skill_count": len(skill_frequency),
        "salary_avg": round(salary_avg) if salary_avg else None,
        "currency": "INR",
    }

    return {
        "total_jobs": total,
        "skill_frequency": skill_frequency,
        "recommendations": recommendations,
        "aggregated_missing_skills": aggregated_missing.most_common(15),
        "top_companies": company_counter.most_common(10),
        "top_locations": location_counter.most_common(10),
        "top_titles": title_counter.most_common(10),
        "employment_type_distribution": dict(emp_type_counter.most_common()),
        "remote_type_distribution": dict(remote_counter.most_common()),
        "salary_distribution": salaries,
        "summary": summary,
        "user_skills": sorted(user_skills),
    }
