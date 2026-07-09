from app.opportunities.services.job_provider_service import (
    search_providers, seed_sample_opportunities,
)
from app.opportunities.services.opportunity_service import (
    search_opportunities, get_opportunity_detail, create_opportunity, update_opportunity,
)
from app.opportunities.services.company_service import (
    get_or_create_company, get_company_insights, search_companies,
)
from app.opportunities.services.salary_service import (
    estimate_salary, get_market_trends,
)
from app.opportunities.services.match_engine import (
    calculate_match_score,
)
from app.opportunities.services.skill_gap_service import (
    analyze_opportunity_skill_gaps,
)
from app.opportunities.services.resume_optimizer import (
    generate_optimized_resume, generate_cover_letter,
    generate_email, generate_linkedin_message, generate_interview_questions,
)
