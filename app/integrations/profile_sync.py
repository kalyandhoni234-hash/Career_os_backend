import logging
from datetime import datetime, timezone
from app.extensions import db
from app.integrations.models import Integration
from app.users.models import Profile
from app.career.models import UserEducation
from app.intelligence.engine import (
    sync_skills_from_source,
    sync_projects_from_source,
    sync_experience_from_source,
    log_event,
)

logger = logging.getLogger(__name__)


def sync_profile_from_github(user_id: int, integration: Integration) -> None:
    pd = integration.provider_data or {}
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.session.add(profile)

    bio = pd.get("bio", "")
    if bio:
        profile.career_summary = bio

    location = pd.get("location", "")
    if location:
        profile.city = location

    languages = pd.get("top_languages", {})
    if languages and isinstance(languages, dict):
        skill_items = [{"name": lang, "source_id": f"github:language:{lang}"} for lang in languages]
        sync_skills_from_source(user_id, skill_items, "github")

    pinned_repos = pd.get("pinned_repos", [])
    if pinned_repos and isinstance(pinned_repos, list):
        project_items = []
        for repo in pinned_repos:
            project_items.append({
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "url": repo.get("url", ""),
                "repo_url": repo.get("url", ""),
                "primary_language": repo.get("language", ""),
                "stars": repo.get("stars", 0),
                "is_pinned": True,
                "source_id": repo.get("url", ""),
            })
        if project_items:
            sync_projects_from_source(user_id, project_items, "github")

    log_event(
        user_id,
        "integration_sync",
        f"GitHub sync: {pd.get('public_repos', 0)} repos, {pd.get('contributions', 0)} contributions",
        f"Synced profile for {integration.provider_username}",
        event_source="github",
    )

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
        exp_items = []
        for exp in experience_list:
            title = exp.get("title", "")
            company = exp.get("companyName", "")
            if title and company:
                exp_items.append({
                    "company": company,
                    "role": title,
                    "description": exp.get("description", ""),
                    "start_date": exp.get("start", ""),
                    "end_date": exp.get("end", ""),
                    "is_current": exp.get("currently_working", False) if "currently_working" in exp else False,
                    "location": exp.get("location", ""),
                    "source_id": f"linkedin:exp:{company}:{title}",
                })
        if exp_items:
            sync_experience_from_source(user_id, exp_items, "linkedin")

    education_list = pd.get("education", [])
    if education_list and isinstance(education_list, list):
        for edu in education_list:
            institution = edu.get("institution", "")
            degree = edu.get("degree", "")
            if institution and degree:
                existing = UserEducation.query.filter_by(
                    user_id=user_id, institution=institution, degree=degree
                ).first()
                if not existing:
                    edu_record = UserEducation(
                        user_id=user_id,
                        institution=institution,
                        degree=degree,
                        branch=edu.get("field", ""),
                        source="linkedin",
                        source_id=f"linkedin:edu:{institution}:{degree}",
                        confidence=0.9,
                        last_synced_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    db.session.add(edu_record)

    skills_list = pd.get("skills", [])
    if skills_list and isinstance(skills_list, list):
        skill_items = []
        for skill_name in skills_list:
            if isinstance(skill_name, dict):
                skill_name = skill_name.get("name", "")
            if not skill_name or not isinstance(skill_name, str):
                continue
            skill_items.append({"name": skill_name, "source_id": f"linkedin:skill:{skill_name}"})
        if skill_items:
            sync_skills_from_source(user_id, skill_items, "linkedin")

    log_event(
        user_id,
        "integration_sync",
        "LinkedIn sync completed",
        f"Synced profile for {integration.provider_username}",
        event_source="linkedin",
    )

    db.session.commit()
    logger.info("Profile synced from LinkedIn for user %s", user_id)


def sync_profile_from_integration(integration: Integration, user_id: int) -> None:
    if integration.provider == "github":
        sync_profile_from_github(user_id, integration)
    elif integration.provider == "linkedin":
        sync_profile_from_linkedin(user_id, integration)
