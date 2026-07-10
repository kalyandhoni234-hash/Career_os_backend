import logging
from typing import Optional
from app.opportunities.models import SalaryInsight, MarketTrend

logger = logging.getLogger(__name__)


SALARY_RANGES = {
    "internship": {"min": 300000, "max": 1200000, "currency": "INR"},
    "entry": {"min": 400000, "max": 1200000, "currency": "INR"},
    "mid": {"min": 1200000, "max": 2500000, "currency": "INR"},
    "senior": {"min": 2500000, "max": 5000000, "currency": "INR"},
    "lead": {"min": 4000000, "max": 8000000, "currency": "INR"},
}


def estimate_salary(
    role: str,
    location: Optional[str] = None,
    experience_level: Optional[str] = None,
    skills: Optional[list[str]] = None,
) -> dict:
    existing = SalaryInsight.query.filter(SalaryInsight.role.ilike(f"%{role}%")).first()

    if existing:
        return {
            "salary_min": existing.salary_min,
            "salary_max": existing.salary_max,
            "market_avg": existing.market_avg,
            "currency": existing.currency,
            "location_diff": existing.location_diff,
            "experience_diff": existing.experience_diff,
            "skill_premium": existing.skill_premium or {},
            "confidence": existing.confidence,
            "source": "database",
        }

    role_lower = role.lower()
    if any(k in role_lower for k in ["intern", "internship", "trainee"]):
        level = "internship"
    elif any(
        k in role_lower for k in ["senior", "lead", "staff", "principal", "architect"]
    ):
        level = "senior" if "senior" in role_lower else "lead"
    elif any(k in role_lower for k in ["junior", "fresher", "entry"]):
        level = "entry"
    else:
        level = (
            "mid" if experience_level in (None, "mid") else experience_level or "mid"
        )

    if experience_level and experience_level in SALARY_RANGES:
        level = experience_level

    base = SALARY_RANGES.get(level, SALARY_RANGES["mid"])

    location_adjust = 1.0
    if location:
        loc_lower = location.lower()
        if any(
            city in loc_lower
            for city in [
                "bangalore",
                "bengaluru",
                "mumbai",
                "pune",
                "hyderabad",
                "gurgaon",
                "delhi",
                "noida",
            ]
        ):
            location_adjust = 1.15
        elif any(
            city in loc_lower
            for city in ["chennai", "kolkata", "ahmedabad", "coimbatore"]
        ):
            location_adjust = 1.0
        elif "remote" in loc_lower:
            location_adjust = 1.05
        else:
            location_adjust = 0.9

    skill_bonus = 0
    skill_premium = {}
    if skills:
        premium_skills = {
            "ai": 25,
            "machine learning": 25,
            "deep learning": 25,
            "llm": 20,
            "nlp": 20,
            "kubernetes": 15,
            "k8s": 15,
            "aws": 10,
            "gcp": 10,
            "azure": 10,
            "react": 5,
            "typescript": 5,
            "python": 5,
            "go": 10,
            "golang": 10,
            "rust": 15,
            "system design": 10,
            "distributed systems": 15,
            "docker": 5,
            "terraform": 10,
            "spark": 10,
            "kafka": 10,
        }
        for skill in skills:
            sl = skill.lower()
            if sl in premium_skills:
                pct = premium_skills[sl]
                skill_bonus = max(skill_bonus, pct)
                skill_premium[skill] = pct

    adj_min = int(base["min"] * location_adjust * (1 + skill_bonus / 100))
    adj_max = int(base["max"] * location_adjust * (1 + skill_bonus / 100))
    market_avg = (adj_min + adj_max) // 2

    return {
        "salary_min": adj_min,
        "salary_max": adj_max,
        "market_avg": market_avg,
        "currency": base["currency"],
        "location_diff": round((location_adjust - 1.0) * 100, 1),
        "experience_diff": 0,
        "skill_premium": skill_premium,
        "confidence": 65,
        "source": "estimate",
    }


MARKET_TRENDS_SAMPLE = [
    {
        "trend_type": "requested_skills",
        "title": "Python",
        "value": "Most Requested",
        "growth_pct": 35.0,
        "category": "Backend",
    },
    {
        "trend_type": "requested_skills",
        "title": "React",
        "value": "2nd Most Requested",
        "growth_pct": 28.0,
        "category": "Frontend",
    },
    {
        "trend_type": "requested_skills",
        "title": "TypeScript",
        "value": "3rd Most Requested",
        "growth_pct": 42.0,
        "category": "Frontend",
    },
    {
        "trend_type": "requested_skills",
        "title": "AWS",
        "value": "4th Most Requested",
        "growth_pct": 22.0,
        "category": "Cloud",
    },
    {
        "trend_type": "requested_skills",
        "title": "Docker",
        "value": "5th Most Requested",
        "growth_pct": 18.0,
        "category": "DevOps",
    },
    {
        "trend_type": "highest_paying",
        "title": "AI/ML Engineer",
        "value": "₹25-45 LPA",
        "growth_pct": 40.0,
        "category": "AI",
    },
    {
        "trend_type": "highest_paying",
        "title": "Staff Engineer",
        "value": "₹35-60 LPA",
        "growth_pct": 15.0,
        "category": "Engineering",
    },
    {
        "trend_type": "highest_paying",
        "title": "Engineering Manager",
        "value": "₹30-55 LPA",
        "growth_pct": 12.0,
        "category": "Management",
    },
    {
        "trend_type": "highest_paying",
        "title": "Data Scientist",
        "value": "₹18-35 LPA",
        "growth_pct": 25.0,
        "category": "Data",
    },
    {
        "trend_type": "trending",
        "title": "Generative AI",
        "value": "Trending",
        "growth_pct": 120.0,
        "category": "AI",
    },
    {
        "trend_type": "trending",
        "title": "Kubernetes",
        "value": "Trending",
        "growth_pct": 45.0,
        "category": "DevOps",
    },
    {
        "trend_type": "trending",
        "title": "System Design",
        "value": "Trending",
        "growth_pct": 55.0,
        "category": "Engineering",
    },
    {
        "trend_type": "hiring_growth",
        "title": "Backend Engineering",
        "value": "High Growth",
        "growth_pct": 32.0,
        "category": "Engineering",
    },
    {
        "trend_type": "hiring_growth",
        "title": "AI/ML",
        "value": "Very High Growth",
        "growth_pct": 65.0,
        "category": "AI",
    },
    {
        "trend_type": "hiring_growth",
        "title": "Cybersecurity",
        "value": "High Growth",
        "growth_pct": 38.0,
        "category": "Security",
    },
    {
        "trend_type": "internship_trends",
        "title": "Software Engineering Intern",
        "value": "Most Common",
        "growth_pct": 20.0,
        "category": "Engineering",
    },
    {
        "trend_type": "internship_trends",
        "title": "Data Science Intern",
        "value": "2nd Most Common",
        "growth_pct": 35.0,
        "category": "Data",
    },
    {
        "trend_type": "internship_trends",
        "title": "AI/ML Intern",
        "value": "Fastest Growing",
        "growth_pct": 80.0,
        "category": "AI",
    },
]


def get_market_trends() -> dict:
    stored = MarketTrend.query.order_by(MarketTrend.created_at.desc()).limit(50).all()
    if stored:
        trends = stored
    else:
        from app.extensions import db

        for entry in MARKET_TRENDS_SAMPLE:
            trend = MarketTrend(**entry)
            db.session.add(trend)
        db.session.commit()
        trends = (
            MarketTrend.query.order_by(MarketTrend.created_at.desc()).limit(50).all()
        )

    result = {}
    for t in trends:
        result.setdefault(t.trend_type, []).append(
            {
                "title": t.title,
                "value": t.value,
                "growth_pct": t.growth_pct,
                "period": t.period,
                "category": t.category,
            }
        )
    return result
