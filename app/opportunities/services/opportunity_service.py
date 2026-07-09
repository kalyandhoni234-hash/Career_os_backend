import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import or_
from app.extensions import db
from app.opportunities.models import Opportunity, CompanyProfile, SavedOpportunity

logger = logging.getLogger(__name__)


def search_opportunities(
    query: Optional[str] = None,
    location: Optional[str] = None,
    remote_type: Optional[str] = None,
    employment_type: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    company: Optional[str] = None,
    tech_stack: Optional[list[str]] = None,
    sort_by: str = "posted_at",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 20,
    min_match_score: Optional[int] = None,
    user_id: Optional[int] = None,
) -> dict:
    q = Opportunity.query.filter_by(is_active=True)

    if query:
        like = f"%{query}%"
        q = q.filter(
            or_(
                Opportunity.title.ilike(like),
                Opportunity.company_name.ilike(like),
                Opportunity.description.ilike(like),
                Opportunity.tech_stack.cast(db.String).ilike(like),
                Opportunity.requirements.cast(db.String).ilike(like),
            )
        )

    if location:
        q = q.filter(Opportunity.location.ilike(f"%{location}%"))
    if remote_type:
        q = q.filter(Opportunity.remote_type == remote_type)
    if employment_type:
        q = q.filter(Opportunity.employment_type == employment_type)
    if salary_min:
        q = q.filter(Opportunity.salary_max >= salary_min)
    if salary_max:
        q = q.filter(Opportunity.salary_min <= salary_max)
    if experience_min is not None:
        q = q.filter(
            or_(
                Opportunity.experience_max >= experience_min,
                Opportunity.experience_max.is_(None),
            )
        )
    if experience_max is not None:
        q = q.filter(
            or_(
                Opportunity.experience_required <= experience_max,
                Opportunity.experience_required.is_(None),
            )
        )
    if company:
        q = q.filter(Opportunity.company_name.ilike(f"%{company}%"))
    if tech_stack:
        for tech in tech_stack:
            q = q.filter(Opportunity.tech_stack.cast(db.String).ilike(f"%{tech}%"))

    sort_col = getattr(Opportunity, sort_by, Opportunity.posted_at)
    order_fn = sort_col.desc if sort_order == "desc" else sort_col.asc
    q = q.order_by(order_fn(), Opportunity.id.desc())

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    # Post-filter by minimum match score if requested
    if min_match_score is not None and user_id is not None:
        from app.opportunities.services.match_engine import calculate_match_score
        scored = []
        for o in items:
            score = calculate_match_score(user_id, o.id)
            if score.get("overall_score", 0) >= min_match_score:
                scored.append((score.get("overall_score", 0), o))
        scored.sort(key=lambda x: x[0], reverse=True)
        items = [o for _, o in scored]
        total = len(items)

    return {
        "opportunities": [_opp_to_dict(o) for o in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


def get_opportunity_detail(opportunity_id: int) -> Optional[dict]:
    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return None
    result = _opp_to_dict(opp, detail=True)

    if opp.company_id:
        company = CompanyProfile.query.get(opp.company_id)
        if company:
            result["company_profile"] = {
                "id": company.id,
                "name": company.name,
                "logo_url": company.logo_url,
                "website": company.website,
                "description": company.description,
                "industry": company.industry,
                "headquarters": company.headquarters,
                "company_size": company.company_size,
                "founded_year": company.founded_year,
                "tech_stack": company.tech_stack or [],
                "interview_difficulty": company.interview_difficulty,
                "glassdoor_rating": company.glassdoor_rating,
                "indeed_rating": company.indeed_rating,
            }
    return result


def create_opportunity(data: dict) -> dict:
    opp = Opportunity(**data)
    db.session.add(opp)
    db.session.commit()
    return _opp_to_dict(opp)


def update_opportunity(opportunity_id: int, data: dict) -> Optional[dict]:
    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return None
    for key, val in data.items():
        if hasattr(opp, key):
            setattr(opp, key, val)
    db.session.commit()
    return _opp_to_dict(opp)


def delete_opportunity(opportunity_id: int) -> bool:
    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return False
    db.session.delete(opp)
    db.session.commit()
    return True


def _opp_to_dict(opp: Opportunity, detail: bool = False) -> dict:
    d = {
        "id": opp.id,
        "title": opp.title,
        "company_name": opp.company_name,
        "company_logo": opp.company_logo,
        "company_url": opp.company_url,
        "location": opp.location,
        "remote_type": opp.remote_type,
        "salary_min": opp.salary_min,
        "salary_max": opp.salary_max,
        "currency": opp.currency,
        "salary_period": opp.salary_period,
        "employment_type": opp.employment_type,
        "experience_required": opp.experience_required,
        "experience_max": opp.experience_max,
        "tech_stack": opp.tech_stack or [],
        "posted_at": opp.posted_at.isoformat() if opp.posted_at else None,
        "created_at": opp.created_at.isoformat() if opp.created_at else None,
        "provider": opp.provider,
        "url": opp.url,
    }
    if detail:
        d.update({
            "description": opp.description,
            "requirements": opp.requirements or [],
            "responsibilities": opp.responsibilities or [],
            "expires_at": opp.expires_at.isoformat() if opp.expires_at else None,
        })
    return d
