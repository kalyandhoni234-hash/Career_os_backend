"""Career Intelligence Engine — single source of truth for all profile data."""

import logging
from datetime import datetime, timezone
from app.extensions import db
from app.intelligence.models import CanonicalProject, CanonicalExperience, CanonicalCertificate, CareerEvent
from app.career.models import UserSkill, UserEducation, UserInterest, UserLanguage, CareerGoal, CareerProfile, UserPreference
from app.users.models import Profile
from app.resume.models import Resume
from app.integrations.models import Integration

logger = logging.getLogger(__name__)

SOURCE_WEIGHTS = {
    "linkedin": 0.9,
    "github": 0.85,
    "resume": 0.8,
    "manual": 1.0,
    "gmail": 0.7,
    "google_drive": 0.6,
}


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_unified_profile(user_id: int) -> dict:
    profile = Profile.query.filter_by(user_id=user_id).first()
    resume = Resume.query.filter_by(user_id=user_id).first()
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    preferences = UserPreference.query.filter_by(user_id=user_id).first()

    skills = get_skills(user_id)
    education = get_education(user_id)
    experience = get_experience(user_id)
    projects = get_projects(user_id)
    interests = get_interests(user_id)
    goals = get_goals(user_id)
    certificates = get_certificates(user_id)
    languages = get_languages(user_id)
    integrations_data = get_integrations_data(user_id)
    events = get_events(user_id)

    linkedin_data = integrations_data.get("linkedin", {})
    github_data = integrations_data.get("github", {})

    return {
        "basic": {
            "full_name": resume.full_name if resume else "",
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "email": linkedin_data.get("email") or (profile and profile.username) or "",
            "phone": resume.phone if resume else "",
            "location": resume.location if resume else profile.city if profile else "",
            "headline": linkedin_data.get("headline") or (profile and profile.career_summary) or "",
            "summary": resume.summary if resume else (profile.career_summary if profile else ""),
            "country": profile.country if profile else "",
            "state": profile.state if profile else "",
            "city": profile.city if profile else "",
            "timezone": profile.timezone if profile else "",
            "date_of_birth": profile.date_of_birth if profile else "",
            "profile_picture": github_data.get("avatar_url") or (profile.profile_picture if profile else ""),
            "gender": profile.gender if profile else "",
        },
        "career": {
            "current_role": cp.position if cp else linkedin_data.get("current_role", ""),
            "current_company": linkedin_data.get("current_company", ""),
            "dream_role": cp.target_role if cp else "",
            "dream_company": cp.target_company if cp else "",
            "career_level": cp.career_level if cp else "",
            "career_stage": cp.career_stage if cp else "student",
            "stage_meta": cp.stage_meta or {} if cp else {},
            "years_experience": cp.years_experience if cp else 0,
            "employment_type": cp.employment_type if cp else "",
            "preferred_industry": cp.preferred_industry if cp else "",
            "work_preference": cp.work_preference if cp else "",
            "target_salary": cp.target_salary if cp else "",
            "target_location": cp.target_location if cp else "",
            "preferred_country": cp.preferred_country if cp else "",
            "target_joining_year": cp.target_joining_year if cp else None,
        },
        "skills": skills,
        "education": education,
        "experience": experience,
        "projects": projects,
        "interests": interests,
        "goals": goals,
        "certificates": certificates,
        "languages": languages,
        "integrations": integrations_data,
        "events": events,
        "preferences": _get_preferences(preferences),
        "sources": _get_source_summary(user_id),
        "completion": _compute_completion(user_id, profile, resume, cp, skills, education, experience, projects, integrations_data),
    }


def get_skills(user_id: int) -> list[dict]:
    rows = UserSkill.query.filter_by(user_id=user_id).order_by(UserSkill.name).all()
    seen = {}
    for row in rows:
        key = row.name.lower()
        if key in seen:
            existing = seen[key]
            if SOURCE_WEIGHTS.get(row.source, 0.5) > SOURCE_WEIGHTS.get(existing.get("source", "manual"), 0.5):
                seen[key] = _skill_to_dict(row)
        else:
            seen[key] = _skill_to_dict(row)
    return sorted(seen.values(), key=lambda x: x["name"].lower())


def _skill_to_dict(row: UserSkill) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "experience_level": row.experience_level,
        "years_of_experience": row.years_of_experience,
        "confidence_rating": row.confidence_rating,
        "source": row.source,
        "source_id": row.source_id,
        "confidence": row.confidence,
        "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
    }


def get_education(user_id: int) -> list[dict]:
    rows = UserEducation.query.filter_by(user_id=user_id).order_by(UserEducation.graduation_year.desc()).all()
    seen = {}
    for row in rows:
        key = (row.institution or "").lower() + "|" + (row.degree or "").lower()
        if key in seen:
            existing = seen[key]
            if SOURCE_WEIGHTS.get(row.source, 0.5) > SOURCE_WEIGHTS.get(existing.get("source", "manual"), 0.5):
                seen[key] = _education_to_dict(row)
        else:
            seen[key] = _education_to_dict(row)
    return list(seen.values())


def _education_to_dict(row: UserEducation) -> dict:
    return {
        "id": row.id,
        "institution": row.institution,
        "degree": row.degree,
        "branch": row.branch or "",
        "specialization": row.specialization or "",
        "graduation_year": row.graduation_year,
        "current_semester": row.current_semester,
        "cgpa": row.cgpa,
        "source": row.source,
        "confidence": row.confidence,
        "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
    }


def get_experience(user_id: int) -> list[dict]:
    rows = CanonicalExperience.query.filter_by(user_id=user_id).order_by(CanonicalExperience.start_date.desc()).all()
    return [_experience_to_dict(r) for r in rows]


def _experience_to_dict(row: CanonicalExperience) -> dict:
    return {
        "id": row.id,
        "company": row.company,
        "role": row.role,
        "location": row.location or "",
        "description": row.description or "",
        "start_date": row.start_date or "",
        "end_date": row.end_date or "",
        "is_current": row.is_current,
        "employment_type": row.employment_type or "",
        "technologies": row.technologies or [],
        "source": row.source,
        "source_id": row.source_id,
        "confidence": row.confidence,
        "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
    }


def get_projects(user_id: int) -> list[dict]:
    rows = CanonicalProject.query.filter_by(user_id=user_id).order_by(CanonicalProject.stars.desc()).all()
    return [_project_to_dict(r) for r in rows]


def _project_to_dict(row: CanonicalProject) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "url": row.url or "",
        "repo_url": row.repo_url or "",
        "primary_language": row.primary_language or "",
        "languages": row.languages or [],
        "stars": row.stars or 0,
        "is_pinned": row.is_pinned,
        "is_fork": row.is_fork,
        "topics": row.topics or [],
        "readme_url": row.readme_url or "",
        "source": row.source,
        "source_id": row.source_id,
        "confidence": row.confidence,
        "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
    }


def get_interests(user_id: int) -> list[dict]:
    rows = UserInterest.query.filter_by(user_id=user_id).all()
    return [{"id": r.id, "name": r.name, "is_custom": r.is_custom} for r in rows]


def get_goals(user_id: int) -> list[dict]:
    rows = CareerGoal.query.filter_by(user_id=user_id).order_by(CareerGoal.priority).all()
    return [
        {
            "id": g.id,
            "title": g.title,
            "target_role": g.target_role or "",
            "target_company": g.target_company or "",
            "status": g.status,
            "priority": g.priority,
            "category": g.category or "career",
            "progress": g.progress or 0,
        }
        for g in rows
    ]


def get_certificates(user_id: int) -> list[dict]:
    rows = CanonicalCertificate.query.filter_by(user_id=user_id).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "issuer": c.issuer or "",
            "url": c.url or "",
            "issue_date": c.issue_date or "",
            "expiry_date": c.expiry_date or "",
            "credential_id": c.credential_id or "",
            "source": c.source,
            "confidence": c.confidence,
        }
        for c in rows
    ]


def get_languages(user_id: int) -> list[dict]:
    rows = UserLanguage.query.filter_by(user_id=user_id).all()
    return [{"id": r.id, "language": r.language, "proficiency": r.proficiency} for r in rows]


def get_integrations_data(user_id: int) -> dict:
    records = Integration.query.filter_by(user_id=user_id).all()
    result = {}
    for rec in records:
        pd = rec.provider_data or {}
        if rec.provider == "github":
            result["github"] = {
                "username": rec.provider_username,
                "avatar_url": pd.get("avatar_url", ""),
                "bio": pd.get("bio", ""),
                "public_repos": pd.get("public_repos", 0),
                "followers": pd.get("followers", 0),
                "contributions": pd.get("contributions", 0),
                "top_languages": pd.get("top_languages", {}),
                "pinned_repos": pd.get("pinned_repos", []),
                "repo_count": pd.get("repositories", 0),
                "connected": True,
                "last_sync": rec.last_sync_at.isoformat() if rec.last_sync_at else None,
            }
        elif rec.provider == "linkedin":
            result["linkedin"] = {
                "email": rec.provider_email,
                "headline": pd.get("headline", ""),
                "current_role": pd.get("current_role", ""),
                "current_company": pd.get("current_company", ""),
                "experience_count": len(pd.get("experience", [])),
                "education_count": len(pd.get("education", [])),
                "skill_count": len(pd.get("skills", [])),
                "connected": True,
                "last_sync": rec.last_sync_at.isoformat() if rec.last_sync_at else None,
            }
        elif rec.provider == "google_calendar":
            result["google_calendar"] = {
                "connected": True,
                "last_sync": rec.last_sync_at.isoformat() if rec.last_sync_at else None,
            }
        elif rec.provider == "google_drive":
            result["google_drive"] = {
                "connected": True,
                "last_sync": rec.last_sync_at.isoformat() if rec.last_sync_at else None,
            }
    return result


def get_events(user_id: int, limit: int = 50) -> list[dict]:
    rows = CareerEvent.query.filter_by(user_id=user_id).order_by(CareerEvent.occurred_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "title": e.title,
            "description": e.description or "",
            "event_source": e.event_source,
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        }
        for e in rows
    ]


def _get_preferences(pref) -> dict:
    if not pref:
        return {}
    return {
        "job_alerts": pref.job_alerts,
        "weekly_ai_review": pref.weekly_ai_review,
        "email_notifications": pref.email_notifications,
        "public_profile": pref.public_profile,
        "resume_visibility": pref.resume_visibility,
        "theme_preference": pref.theme_preference,
        "ai_tone": pref.ai_tone or "professional",
        "reminder_freq": pref.reminder_freq or "weekly",
        "weekly_reports": pref.weekly_reports if pref.weekly_reports is not None else True,
        "roadmap_gen": pref.roadmap_gen if pref.roadmap_gen is not None else True,
        "daily_motivation": pref.daily_motivation if pref.daily_motivation is not None else True,
    }


def _get_source_summary(user_id: int) -> dict:
    skills = UserSkill.query.filter_by(user_id=user_id).all()
    skill_sources = {}
    for s in skills:
        src = s.source or "manual"
        if src not in skill_sources:
            skill_sources[src] = 0
        skill_sources[src] += 1

    return {
        "skill_sources": skill_sources,
        "total_skills": len(skills),
        "projects_count": CanonicalProject.query.filter_by(user_id=user_id).count(),
        "experience_count": CanonicalExperience.query.filter_by(user_id=user_id).count(),
        "certificates_count": CanonicalCertificate.query.filter_by(user_id=user_id).count(),
    }


def _compute_completion(user_id: int, profile, resume, cp, skills, education, experience, projects, integrations) -> dict:
    score = 0
    total = 0
    breakdown = {}

    checks = [
        ("has_resume", resume is not None, 10),
        ("has_summary", bool(resume and resume.summary), 5),
        ("has_full_name", bool(resume and resume.full_name), 5),
        ("has_photo", bool(profile and profile.profile_picture), 5),
        ("has_country", bool(profile and profile.country), 5),
        ("has_city", bool(profile and profile.city), 5),
        ("has_phone", bool(profile and profile.phone_number), 5),
        ("has_dob", bool(profile and profile.date_of_birth), 5),
        ("has_education", len(education) > 0, 10),
        ("has_experience", len(experience) > 0, 10),
        ("has_skills", len(skills) > 0, 10),
        ("has_projects", len(projects) > 0, 10),
        ("has_goals", CareerGoal.query.filter_by(user_id=user_id).count() > 0, 5),
        ("has_interests", len(get_interests(user_id)) > 0, 5),
        ("github_connected", integrations.get("github", {}).get("connected", False), 10),
        ("linkedin_connected", integrations.get("linkedin", {}).get("connected", False), 10),
    ]

    for key, done, weight in checks:
        total += weight
        if done:
            score += weight
        breakdown[key] = {"done": done, "weight": weight, "earned": weight if done else 0}

    pct = round((score / total) * 100) if total > 0 else 0
    return {"score": pct, "breakdown": breakdown}


def sync_skills_from_source(user_id: int, skills: list[dict], source: str) -> list[int]:
    created_ids = []
    for item in skills:
        name = (item.get("name", "") if isinstance(item, dict) else str(item)).strip()
        if not name:
            continue
        source_id = item.get("source_id", "") if isinstance(item, dict) else ""
        existing = UserSkill.query.filter_by(user_id=user_id, name=name).first()
        if existing:
            existing_source_weight = SOURCE_WEIGHTS.get(existing.source or "manual", 0.5)
            new_source_weight = SOURCE_WEIGHTS.get(source, 0.5)
            if new_source_weight > existing_source_weight:
                existing.source = source
                existing.source_id = source_id
                existing.confidence = new_source_weight
                existing.last_synced_at = _now()
            elif existing.source == source and source_id:
                existing.source_id = source_id
                existing.last_synced_at = _now()
            created_ids.append(existing.id)
        else:
            confidence = SOURCE_WEIGHTS.get(source, 0.5)
            level = item.get("experience_level", "intermediate") if isinstance(item, dict) else "intermediate"
            new_skill = UserSkill(
                user_id=user_id,
                name=name,
                experience_level=level,
                years_of_experience=item.get("years_of_experience", 0) if isinstance(item, dict) else 0,
                confidence_rating=round(confidence * 5),
                source=source,
                source_id=source_id,
                confidence=confidence,
                last_synced_at=_now(),
            )
            db.session.add(new_skill)
            db.session.flush()
            created_ids.append(new_skill.id)
    return created_ids


def sync_projects_from_source(user_id: int, projects: list[dict], source: str) -> list[int]:
    created_ids = []
    for item in projects:
        name = item.get("name", "").strip()
        if not name:
            continue
        source_id = item.get("source_id", item.get("url", ""))
        existing = CanonicalProject.query.filter_by(user_id=user_id, source=source, source_id=source_id).first()
        if existing:
            for field in ["description", "url", "repo_url", "primary_language", "languages", "stars", "is_pinned", "is_fork", "topics", "readme_url"]:
                if field in item:
                    setattr(existing, field, item[field])
            existing.last_synced_at = _now()
            existing.confidence = max(existing.confidence, SOURCE_WEIGHTS.get(source, 0.5))
            created_ids.append(existing.id)
        else:
            new_proj = CanonicalProject(
                user_id=user_id,
                name=name,
                description=item.get("description", ""),
                url=item.get("url", ""),
                repo_url=item.get("repo_url", item.get("url", "")),
                primary_language=item.get("primary_language", ""),
                languages=item.get("languages", []),
                stars=item.get("stars", 0),
                is_pinned=item.get("is_pinned", False),
                is_fork=item.get("is_fork", False),
                topics=item.get("topics", []),
                readme_url=item.get("readme_url", ""),
                source=source,
                source_id=source_id,
                confidence=SOURCE_WEIGHTS.get(source, 0.5),
                last_synced_at=_now(),
            )
            db.session.add(new_proj)
            db.session.flush()
            created_ids.append(new_proj.id)
    return created_ids


def sync_experience_from_source(user_id: int, experience: list[dict], source: str) -> list[int]:
    created_ids = []
    for item in experience:
        company = item.get("company", "").strip()
        role = item.get("role", item.get("title", "")).strip()
        if not company or not role:
            continue
        source_id = item.get("source_id", f"{company}|{role}")
        existing = CanonicalExperience.query.filter_by(user_id=user_id, source=source, source_id=source_id).first()
        if existing:
            for field in ["company", "role", "location", "description", "start_date", "end_date", "is_current", "employment_type", "technologies"]:
                if field in item:
                    setattr(existing, field, item[field])
            existing.last_synced_at = _now()
            existing.confidence = max(existing.confidence, SOURCE_WEIGHTS.get(source, 0.5))
            created_ids.append(existing.id)
        else:
            new_exp = CanonicalExperience(
                user_id=user_id,
                company=company,
                role=role,
                location=item.get("location", ""),
                description=item.get("description", ""),
                start_date=item.get("start_date", ""),
                end_date=item.get("end_date", ""),
                is_current=item.get("is_current", False),
                employment_type=item.get("employment_type", ""),
                technologies=item.get("technologies", []),
                source=source,
                source_id=source_id,
                confidence=SOURCE_WEIGHTS.get(source, 0.5),
                last_synced_at=_now(),
            )
            db.session.add(new_exp)
            db.session.flush()
            created_ids.append(new_exp.id)
    return created_ids


def log_event(user_id: int, event_type: str, title: str, description: str = "", event_source: str = "manual", source_id: str = ""):
    try:
        event = CareerEvent(
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            event_source=event_source,
            source_id=source_id,
            occurred_at=_now(),
        )
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning("Failed to log career event: %s", e)
