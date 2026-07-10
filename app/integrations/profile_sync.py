import logging
from datetime import datetime, timezone
from app.extensions import db
from app.integrations.models import Integration
from app.users.models import Profile
from app.career.models import UserSkill, UserEducation, CareerTimelineEvent

logger = logging.getLogger(__name__)

LANGUAGE_LEVEL_MAP = {
    "python": "intermediate",
    "javascript": "intermediate",
    "typescript": "intermediate",
    "java": "intermediate",
    "go": "intermediate",
    "rust": "intermediate",
    "cpp": "intermediate",
    "c++": "intermediate",
    "c": "intermediate",
    "ruby": "intermediate",
    "php": "intermediate",
    "swift": "intermediate",
    "kotlin": "intermediate",
    "scala": "intermediate",
    "dart": "intermediate",
    "elixir": "intermediate",
    "haskell": "intermediate",
    "r": "intermediate",
    "sql": "intermediate",
    "html": "intermediate",
    "css": "intermediate",
    "shell": "intermediate",
    "powershell": "intermediate",
    "jupyter": "intermediate",
}


def sync_profile_from_github(user_id: int, integration: Integration) -> None:
    pd = integration.provider_data or {}
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.session.add(profile)

    bio = pd.get("bio", "")
    if bio:
        profile.career_summary = bio

    company = pd.get("company", "")
    location = pd.get("location", "")
    if company and not profile.experience:
        profile.experience = company
    if location:
        profile.city = location

    languages = pd.get("top_languages", {})
    if languages and isinstance(languages, dict):
        for lang_name in languages:
            existing = UserSkill.query.filter_by(
                user_id=user_id, name=lang_name
            ).first()
            if not existing:
                level = LANGUAGE_LEVEL_MAP.get(lang_name.lower(), "beginner")
                skill = UserSkill(
                    user_id=user_id,
                    name=lang_name,
                    experience_level=level,
                    confidence_rating=2,
                )
                db.session.add(skill)

    event = CareerTimelineEvent(
        user_id=user_id,
        event_type="integration_sync",
        title=f"GitHub sync: {pd.get('public_repos', 0)} repos, {pd.get('contributions', 0)} contributions",
        description=f"Synced profile for {integration.provider_username}",
        event_date=datetime.now(timezone.utc).replace(tzinfo=None),
        importance=1,
        visibility="private",
    )
    db.session.add(event)

    db.session.commit()
    logger.info("Profile synced from GitHub for user %s", user_id)


def sync_profile_from_linkedin(user_id: int, integration: Integration) -> None:
    pd = integration.provider_data or {}
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.session.add(profile)

    name = pd.get("name", "")
    if name:
        parts = name.split(" ", 1)
        profile.first_name = parts[0] if parts else ""
        profile.last_name = parts[1] if len(parts) > 1 else ""

    headline = pd.get("headline", "")
    if headline:
        profile.career_summary = headline

    experience_list = pd.get("experience", [])
    if experience_list and isinstance(experience_list, list):
        exp_texts = []
        for exp in experience_list:
            title = exp.get("title", "")
            company = exp.get("companyName", "")
            if title and company:
                exp_texts.append(f"{title} at {company}")
            elif title:
                exp_texts.append(title)
        if exp_texts:
            profile.experience = "\n".join(exp_texts)

    education_list = pd.get("education", [])
    if education_list and isinstance(education_list, list):
        for edu in education_list:
            institution = edu.get("institution", "")
            degree = edu.get("degree", "")
            if institution and degree:
                existing = UserEducation.query.filter_by(
                    user_id=user_id, institution=institution
                ).first()
                if not existing:
                    edu_record = UserEducation(
                        user_id=user_id,
                        institution=institution,
                        degree=degree,
                    )
                    db.session.add(edu_record)

    skills_list = pd.get("skills", [])
    if skills_list and isinstance(skills_list, list):
        for skill_name in skills_list:
            if isinstance(skill_name, dict):
                skill_name = skill_name.get("name", "")
            if not skill_name or not isinstance(skill_name, str):
                continue
            existing = UserSkill.query.filter_by(
                user_id=user_id, name=skill_name
            ).first()
            if not existing:
                skill = UserSkill(
                    user_id=user_id,
                    name=skill_name,
                    experience_level="intermediate",
                    confidence_rating=3,
                )
                db.session.add(skill)

    event = CareerTimelineEvent(
        user_id=user_id,
        event_type="integration_sync",
        title="LinkedIn sync completed",
        description=f"Synced profile for {integration.provider_username}",
        event_date=datetime.now(timezone.utc).replace(tzinfo=None),
        importance=1,
        visibility="private",
    )
    db.session.add(event)

    db.session.commit()
    logger.info("Profile synced from LinkedIn for user %s", user_id)


def sync_profile_from_integration(integration: Integration, user_id: int) -> None:
    if integration.provider == "github":
        sync_profile_from_github(user_id, integration)
    elif integration.provider == "linkedin":
        sync_profile_from_linkedin(user_id, integration)
