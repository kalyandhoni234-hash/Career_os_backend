"""Bridge between the Resume table and canonical profile tables.

Translates canonical data (Profile, UserSkill, CanonicalExperience, etc.)
into ResumeData JSON format and vice versa, so Resume Studio can read from
the unified career profile while storing only resume-specific overrides.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.core.session import safe_commit
from app.users.models import Profile
from app.career.models import (
    UserSkill,
    UserEducation,
    UserLanguage,
    CareerProfile,
)
from app.intelligence.models import (
    CanonicalProject,
    CanonicalExperience,
    CanonicalCertificate,
)
from app.resume.models import Resume
from app.intelligence.engine import (
    sync_skills_from_source,
    sync_projects_from_source,
    sync_experience_from_source,
)


# ── Convert canonical → ResumeData JSON format ────────────


def _profile_to_resume(user_id):
    """Read Profile + User + CareerProfile into ResumeData personal fields."""
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return {}

    full_name = (
        f"{profile.first_name or ''} {profile.last_name or ''}".strip()
    )

    career_profile = CareerProfile.query.filter_by(user_id=user_id).first()

    return {
        "full_name": full_name,
        "phone": profile.phone_number or "",
        "location": profile.city or "",
        "summary": profile.career_summary or "",
        "title": career_profile.target_role if career_profile else "",
    }


def _skills_to_resume(user_id):
    """Read UserSkill names into Resume skills[]."""
    skills = (
        UserSkill.query.filter_by(user_id=user_id)
        .order_by(UserSkill.name)
        .all()
    )
    return [s.name for s in skills if s.name]


def _experience_to_resume(user_id):
    """Convert CanonicalExperience rows → Resume experience[] entries."""
    rows = (
        CanonicalExperience.query.filter_by(user_id=user_id)
        .order_by(CanonicalExperience.start_date.desc().nullslast())
        .all()
    )
    result = []
    for exp in rows:
        bullets = [exp.description] if exp.description else [""]
        techs = exp.technologies if exp.technologies else []
        result.append(
            {
                "company": exp.company or "",
                "role": exp.role or "",
                "start": exp.start_date or "",
                "end": exp.end_date or "",
                "bullets": bullets,
                "technologies": techs,
            }
        )
    return result


def _education_to_resume(user_id):
    """Convert UserEducation rows → Resume education[] entries."""
    rows = (
        UserEducation.query.filter_by(user_id=user_id)
        .order_by(UserEducation.graduation_year.desc().nullslast())
        .all()
    )
    result = []
    for edu in rows:
        result.append(
            {
                "school": edu.institution or "",
                "degree": edu.degree or "",
                "field": edu.branch or "",
                "start": "",
                "end": str(edu.graduation_year) if edu.graduation_year else "",
                "gpa": str(edu.cgpa) if edu.cgpa else "",
            }
        )
    return result


def _projects_to_resume(user_id):
    """Convert CanonicalProject rows → Resume projects[] entries."""
    rows = (
        CanonicalProject.query.filter_by(user_id=user_id)
        .order_by(CanonicalProject.stars.desc().nullslast())
        .all()
    )
    result = []
    for proj in rows:
        techs = []
        if proj.primary_language:
            techs.append(proj.primary_language)
        if proj.languages:
            for lang in proj.languages:
                if lang not in techs:
                    techs.append(lang)
        result.append(
            {
                "name": proj.name or "",
                "description": proj.description or "",
                "technologies": techs,
                "url": proj.url or "",
                "github": proj.repo_url or "",
            }
        )
    return result


def _certificates_to_resume(user_id):
    """Convert CanonicalCertificate rows → Resume certificates[] entries."""
    rows = (
        CanonicalCertificate.query.filter_by(user_id=user_id)
        .order_by(CanonicalCertificate.issue_date.desc().nullslast())
        .all()
    )
    result = []
    for cert in rows:
        result.append(
            {
                "name": cert.name or "",
                "issuer": cert.issuer or "",
                "date": cert.issue_date or "",
                "url": cert.url or "",
            }
        )
    return result


def _languages_to_resume(user_id):
    """Convert UserLanguage rows → Resume languages[] entries."""
    rows = UserLanguage.query.filter_by(user_id=user_id).all()
    result = []
    for lang in rows:
        result.append(
            {
                "name": lang.language or "",
                "level": lang.proficiency or "",
            }
        )
    return result


# ── Merge: resume record over canonical ───────────────────


def get_merged_resume(user_id):
    """Build a full ResumeData dict by merging canonical profile data
    with the stored Resume record.  Resume record values win on conflict
    so manual edits always take precedence."""
    resume = Resume.query.filter_by(user_id=user_id).first()
    canonical_exists = Profile.query.filter_by(user_id=user_id).first() is not None

    # If neither a resume record nor any canonical profile data exists,
    # return None so the frontend shows a blank slate.
    if not resume and not canonical_exists:
        return None

    # Start with canonical data
    merged = {
        "id": resume.id if resume else 0,
        "full_name": "",
        "email": "",
        "phone": "",
        "location": "",
        "summary": "",
        "title": "",
        "website": "",
        "linkedin": "",
        "github": "",
        "portfolio": "",
        "experience": [],
        "education": [],
        "projects": [],
        "skills": [],
        "certificates": [],
        "achievements": [],
        "languages": [],
        "publications": [],
        "tone": "professional",
        "target_job_description": "",
        "created_at": resume.created_at.isoformat() if resume and resume.created_at else None,
        "updated_at": resume.updated_at.isoformat() if resume and resume.updated_at else None,
    }

    # Overlay canonical data
    merged.update(_profile_to_resume(user_id))
    merged["skills"] = _skills_to_resume(user_id)
    merged["experience"] = _experience_to_resume(user_id)
    merged["education"] = _education_to_resume(user_id)
    merged["projects"] = _projects_to_resume(user_id)
    merged["certificates"] = _certificates_to_resume(user_id)
    merged["languages"] = _languages_to_resume(user_id)

    # Overlay resume-record values (manual edits take precedence)
    if resume:
        for field in (
            "full_name",
            "email",
            "phone",
            "location",
            "summary",
            "title",
            "website",
            "linkedin",
            "github",
            "portfolio",
            "tone",
            "target_job_description",
        ):
            val = getattr(resume, field, None)
            if val:
                merged[field] = val

        for array_field in (
            "experience",
            "education",
            "projects",
            "skills",
            "certificates",
            "achievements",
            "languages",
            "publications",
        ):
            val = getattr(resume, array_field, None)
            if val:
                merged[array_field] = val

    return merged


# ── Write ResumeData back to canonical tables ────────────


def save_resume_to_canonical(user_id, resume_data):
    """Propagate ResumeData fields saved in Resume Studio back into
    the canonical profile tables so the unified profile stays in sync."""
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.session.add(profile)

    # Personal info → Profile
    full_name = resume_data.get("full_name", "")
    if full_name:
        parts = full_name.split(" ", 1)
        profile.first_name = parts[0]
        profile.last_name = parts[1] if len(parts) > 1 else ""
    profile.phone_number = resume_data.get("phone", "")
    profile.city = resume_data.get("location", "")
    profile.career_summary = resume_data.get("summary", "")

    # Skills → UserSkill with manual source (weight 1.0)
    skills = resume_data.get("skills", [])
    if skills and isinstance(skills, list):
        skill_items = [
            {"name": s, "source_id": f"manual:resume:{s}"}
            for s in skills
            if s and isinstance(s, str)
        ]
        if skill_items:
            sync_skills_from_source(user_id, skill_items, "manual")

    # Experience → CanonicalExperience
    exp_list = resume_data.get("experience", [])
    if exp_list and isinstance(exp_list, list):
        exp_items = []
        for exp in exp_list:
            company = exp.get("company", "")
            role = exp.get("role", "")
            if not company or not role:
                continue
            exp_items.append(
                {
                    "company": company,
                    "role": role,
                    "description": "\n".join(
                        b for b in exp.get("bullets", []) if b
                    ),
                    "start_date": exp.get("start", ""),
                    "end_date": exp.get("end", ""),
                    "technologies": exp.get("technologies", []),
                    "source_id": f"manual:resume:{company}:{role}",
                }
            )
        if exp_items:
            sync_experience_from_source(user_id, exp_items, "manual")

    # Education → UserEducation
    edu_list = resume_data.get("education", [])
    if edu_list and isinstance(edu_list, list):
        for edu in edu_list:
            institution = edu.get("school", "")
            degree = edu.get("degree", "")
            if not institution:
                continue
            existing = UserEducation.query.filter_by(
                user_id=user_id, institution=institution, degree=degree
            ).first()
            if not existing:
                cgpa = None
                gpa_str = edu.get("gpa", "")
                if gpa_str:
                    try:
                        cgpa = float(gpa_str)
                    except ValueError:
                        cgpa = None
                db.session.add(
                    UserEducation(
                        user_id=user_id,
                        institution=institution,
                        degree=degree,
                        branch=edu.get("field", ""),
                        cgpa=cgpa,
                        source="manual",
                        source_id=f"manual:resume:{institution}:{degree}",
                        confidence=1.0,
                        last_synced_at=datetime.now(timezone.utc).replace(
                            tzinfo=None
                        ),
                    )
                )

    # Projects → CanonicalProject
    proj_list = resume_data.get("projects", [])
    if proj_list and isinstance(proj_list, list):
        proj_items = []
        for proj in proj_list:
            name = proj.get("name", "")
            if not name:
                continue
            proj_items.append(
                {
                    "name": name,
                    "description": proj.get("description", ""),
                    "url": proj.get("url", ""),
                    "repo_url": proj.get("github", ""),
                    "primary_language": (
                        proj.get("technologies", [""])[0]
                        if proj.get("technologies")
                        else ""
                    ),
                    "languages": proj.get("technologies", []),
                    "source_id": f"manual:resume:{name}",
                }
            )
        if proj_items:
            sync_projects_from_source(user_id, proj_items, "manual")

    # Certificates → CanonicalCertificate
    cert_list = resume_data.get("certificates", [])
    if cert_list and isinstance(cert_list, list):
        for cert in cert_list:
            name = cert.get("name", "")
            if not name:
                continue
            existing = CanonicalCertificate.query.filter_by(
                user_id=user_id,
                source="manual",
                source_id=f"manual:resume:{name}",
            ).first()
            if not existing:
                db.session.add(
                    CanonicalCertificate(
                        user_id=user_id,
                        name=name,
                        issuer=cert.get("issuer", ""),
                        url=cert.get("url", ""),
                        issue_date=cert.get("date", ""),
                        source="manual",
                        source_id=f"manual:resume:{name}",
                        confidence=1.0,
                        last_synced_at=datetime.now(timezone.utc).replace(
                            tzinfo=None
                        ),
                    )
                )

    # Languages → UserLanguage
    lang_list = resume_data.get("languages", [])
    if lang_list and isinstance(lang_list, list):
        for lang_data in lang_list:
            name = ""
            proficiency = ""
            if isinstance(lang_data, dict):
                name = lang_data.get("name", "")
                proficiency = lang_data.get("level", "")
            elif isinstance(lang_data, str):
                name = lang_data
            if not name:
                continue
            existing = UserLanguage.query.filter_by(
                user_id=user_id, language=name
            ).first()
            if not existing:
                db.session.add(
                    UserLanguage(
                        user_id=user_id,
                        language=name,
                        proficiency=proficiency or "intermediate",
                    )
                )
            elif proficiency:
                existing.proficiency = proficiency

    safe_commit()
