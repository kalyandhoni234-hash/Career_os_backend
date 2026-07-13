from app.opportunities.services.job_provider_service import (
    search_providers as search_providers,
    seed_sample_opportunities as seed_sample_opportunities,
)
from app.opportunities.services.opportunity_service import (
    search_opportunities as search_opportunities,
    get_opportunity_detail as get_opportunity_detail,
    create_opportunity as create_opportunity,
    update_opportunity as update_opportunity,
)
from app.opportunities.services.company_service import (
    get_or_create_company as get_or_create_company,
    get_company_insights as get_company_insights,
    search_companies as search_companies,
)
from app.opportunities.services.salary_service import (
    estimate_salary as estimate_salary,
    get_market_trends as get_market_trends,
)
from app.opportunities.services.match_engine import (
    calculate_match_score as calculate_match_score,
)
from app.opportunities.services.skill_gap_service import (
    analyze_opportunity_skill_gaps as analyze_opportunity_skill_gaps,
)
from app.opportunities.services.resume_optimizer import (
    generate_optimized_resume as generate_optimized_resume,
    generate_cover_letter as generate_cover_letter,
    generate_email as generate_email,
    generate_linkedin_message as generate_linkedin_message,
    generate_interview_questions as generate_interview_questions,
)
from app.opportunities.services.job_parser import (
    parse_job_url as parse_job_url,
    detect_platform as detect_platform,
)
from app.opportunities.services.opportunity_intelligence_service import (
    compute_opportunity_intelligence as compute_opportunity_intelligence,
)
from app.opportunities.services.career_agent_service import (
    generate_prioritized_actions as generate_prioritized_actions,
    generate_ai_career_advice as generate_ai_career_advice,
)
from app.opportunities.services.health_score_service import (
    compute_application_health as compute_application_health,
    compute_health_for_all_saved as compute_health_for_all_saved,
)
from app.opportunities.services.predictive_analytics_service import (
    compute_predictive_analytics as compute_predictive_analytics,
)
