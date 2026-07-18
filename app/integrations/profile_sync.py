import logging
from datetime import datetime, timezone
from app.extensions import db
from app.integrations.models import Integration
from app.users.models import Profile
from app.career.models import UserEducation
from app.resume.models import Resume
from app.intelligence.engine import (
    sync_skills_from_source,
    sync_projects_from_source,
    sync_experience_from_source,
    log_event,
)

logger = logging.getLogger(__name__)


def _format_li_date(date_dict):
    """Format a LinkedIn date dict {year, month, day?} to 'YYYY-MM' string."""
    if not date_dict or not isinstance(date_dict, dict):
        return ""
    year = date_dict.get("year", "")
    month = date_dict.get("month", "")
    if year and month:
        return f"{year}-{int(month):02d}"
    return str(year) if year else ""


def _sync_resume_section(resume, field, value):
    """Set a resume field only if currently empty, to preserve manual edits."""
    if value is None:
        return
    current = getattr(resume, field, None)
    if not current:
        setattr(resume, field, value)


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

    # --- Populate Resume table for Resume Studio ---
    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        resume = Resume(user_id=user_id)
        db.session.add(resume)

    _sync_resume_section(resume, "full_name", pd.get("name", ""))
    _sync_resume_section(resume, "location", pd.get("location", ""))
    _sync_resume_section(resume, "website", pd.get("blog", ""))
    _sync_resume_section(resume, "summary", pd.get("bio", ""))

    github_url = f"https://github.com/{integration.provider_username}" if integration.provider_username else ""
    _sync_resume_section(resume, "github", github_url)

    top_langs = pd.get("top_languages", {})
    if top_langs and isinstance(top_langs, dict):
        existing = set(resume.skills or [])
        new_langs = [lang for lang in top_langs if lang and lang not in existing]
        if new_langs:
            resume.skills = list(existing | set(new_langs))

    pinned = pd.get("pinned_repos", [])
    if pinned and isinstance(pinned, list):
        if not resume.projects:
            resume.projects = [
                {
                    "name": r.get("name", ""),
                    "description": r.get("description", ""),
                    "technologies": [r.get("language", "")] if r.get("language") else [],
                    "url": r.get("url", ""),
                    "github": r.get("url", ""),
                }
                for r in pinned
            ]

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
    logger.debug(
        "SYNC PROFILE LINKEDIN START: user=%s experience=%d education=%d skills=%d",
        user_id,
        len(pd.get("experience", [])),
        len(pd.get("education", [])),
        len(pd.get("skills", [])),
    )

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
        logger.debug("SYNC PROFILE LINKEDIN: built %d exp_items from %d raw experience entries", len(exp_items), len(experience_list))
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
                        branch=edu.get("fieldOfStudy", ""),
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
        logger.debug("SYNC PROFILE LINKEDIN: built %d skill_items from %d raw skills", len(skill_items), len(skills_list))
        if skill_items:
            sync_skills_from_source(user_id, skill_items, "linkedin")

    # --- Populate Resume table for Resume Studio ---
    resume = Resume.query.filter_by(user_id=user_id).first()
    if not resume:
        resume = Resume(user_id=user_id)
        db.session.add(resume)
    logger.debug("SYNC PROFILE LINKEDIN: resume id=%s exists=%s", resume.id if resume.id else "(new)", resume.id is not None)

    _sync_resume_section(resume, "full_name", pd.get("name", ""))

    headline_text = pd.get("headline", "")
    if headline_text and " at " in headline_text:
        _sync_resume_section(resume, "title", headline_text.split(" at ")[0].strip())
    elif headline_text:
        _sync_resume_section(resume, "summary", headline_text)

    vanity = pd.get("vanity_name", "")
    if vanity:
        _sync_resume_section(resume, "linkedin", f"https://linkedin.com/in/{vanity}")

    li_skills = pd.get("skills", [])
    if li_skills and isinstance(li_skills, list):
        existing = set(resume.skills or [])
        new_li = [s for s in li_skills if isinstance(s, str) and s and s not in existing]
        if new_li:
            resume.skills = list(existing | set(new_li))

    exp_list = pd.get("experience", [])
    if exp_list and isinstance(exp_list, list) and not resume.experience:
        resume.experience = []
        for e in exp_list:
            company = e.get("companyName", "")
            role = e.get("title", "")
            if not company or not role:
                continue
            resume.experience.append({
                "company": company,
                "role": role,
                "start": _format_li_date(e.get("start", {})),
                "end": _format_li_date(e.get("end", {})),
                "bullets": [""],
                "technologies": [],
            })

    edu_list = pd.get("education", [])
    if edu_list and isinstance(edu_list, list) and not resume.education:
        resume.education = []
        for e in edu_list:
            inst = e.get("institution", "")
            degree = e.get("degree", "")
            if not inst:
                continue
            resume.education.append({
                "school": inst,
                "degree": degree,
                "field": e.get("fieldOfStudy", ""),
                "start": _format_li_date(e.get("start", {})),
                "end": _format_li_date(e.get("end", {})),
                "gpa": "",
            })

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
