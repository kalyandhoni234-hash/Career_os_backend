import logging
from typing import Optional
from app.extensions import db
from app.opportunities.models import CompanyProfile

logger = logging.getLogger(__name__)


def get_or_create_company(name: str) -> CompanyProfile:
    company = CompanyProfile.query.filter_by(name=name).first()
    if company:
        return company
    company = CompanyProfile(name=name)
    db.session.add(company)
    db.session.commit()
    return company


def get_company_insights(company_name: str) -> Optional[dict]:
    company = CompanyProfile.query.filter_by(name=company_name).first()
    if not company:
        company = CompanyProfile.query.filter(
            CompanyProfile.name.ilike(f"%{company_name}%")
        ).first()
    if not company:
        return None

    from app.opportunities.models import Opportunity

    active_jobs = Opportunity.query.filter_by(
        company_name=company.name, is_active=True
    ).count()

    return {
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
        "products": company.products or [],
        "hiring_trends": company.hiring_trends,
        "recent_news": company.recent_news or [],
        "interview_difficulty": company.interview_difficulty,
        "engineering_culture": company.engineering_culture,
        "application_tips": company.application_tips,
        "expected_salary": company.expected_salary,
        "interview_process": company.interview_process or [],
        "linkedin_url": company.linkedin_url,
        "glassdoor_rating": company.glassdoor_rating,
        "indeed_rating": company.indeed_rating,
        "active_jobs_count": active_jobs,
    }


def search_companies(query: str, page: int = 1, per_page: int = 20) -> dict:
    q = CompanyProfile.query
    if query:
        like = f"%{query}%"
        q = q.filter(CompanyProfile.name.ilike(like))

    total = q.count()
    items = (
        q.order_by(CompanyProfile.name.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "companies": [
            {
                "id": c.id,
                "name": c.name,
                "logo_url": c.logo_url,
                "website": c.website,
                "industry": c.industry,
                "headquarters": c.headquarters,
                "company_size": c.company_size,
                "linkedin_url": c.linkedin_url,
            }
            for c in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
