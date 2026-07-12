import logging
import json

logger = logging.getLogger(__name__)


def _collect_profile_data(user_id):
    """Read unified career profile from canonical tables."""
    from app.users.models import Profile
    from app.career.models import (
        UserSkill, UserEducation, UserLanguage,
        CareerProfile
    )
    from app.intelligence.models import (
        CanonicalExperience, CanonicalProject, CanonicalCertificate
    )

    profile = Profile.query.filter_by(user_id=user_id).first()
    cp = CareerProfile.query.filter_by(user_id=user_id).first()

    full_name = ""
    email = ""
    phone = ""
    location = ""
    if profile:
        full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        phone = profile.phone_number or ""
        location = f"{profile.city or ''}, {profile.country or ''}".strip(", ")

    from flask_login import current_user
    try:
        email = current_user.email or ""
    except RuntimeError:
        email = ""

    skills = [
        {"name": s.name, "level": s.experience_level or "intermediate"}
        for s in UserSkill.query.filter_by(user_id=user_id).order_by(UserSkill.name).all()
    ]

    education = [
        {
            "institution": e.institution,
            "degree": e.degree,
            "field": e.branch or "",
            "graduation_year": e.graduation_year,
            "cgpa": e.cgpa,
        }
        for e in UserEducation.query.filter_by(user_id=user_id)
        .order_by(UserEducation.graduation_year.desc())
        .all()
    ]

    experience = [
        {
            "company": e.company,
            "role": e.role,
            "start_date": e.start_date,
            "end_date": e.end_date or "Present",
            "description": e.description or "",
            "technologies": e.technologies or [],
        }
        for e in CanonicalExperience.query.filter_by(user_id=user_id)
        .order_by(CanonicalExperience.start_date.desc().nullslast())
        .all()
    ]

    projects = [
        {
            "name": p.name,
            "description": p.description or "",
            "technologies": p.technologies or [],
            "url": p.url or "",
        }
        for p in CanonicalProject.query.filter_by(user_id=user_id)
        .order_by(CanonicalProject.created_at.desc())
        .all()
    ]

    certificates = [
        {
            "name": c.name,
            "issuer": c.issuer or "",
            "date": c.date or "",
        }
        for c in CanonicalCertificate.query.filter_by(user_id=user_id).all()
    ]

    languages = [
        {"name": ul.language, "proficiency": ul.proficiency}
        for ul in UserLanguage.query.filter_by(user_id=user_id).all()
    ]

    target_role = cp.target_role if cp else ""
    summary = profile.career_summary if profile and profile.career_summary else ""

    return {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "location": location,
        "target_role": target_role,
        "summary": summary,
        "skills": skills,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certificates": certificates,
        "languages": languages,
    }


def _profile_to_prompt(profile_data: dict) -> str:
    """Convert profile data to a structured prompt for the AI."""
    lines = []

    lines.append(f"Full Name: {profile_data['full_name'] or 'Not provided'}")
    lines.append(f"Email: {profile_data['email'] or 'Not provided'}")
    lines.append(f"Phone: {profile_data['phone'] or 'Not provided'}")
    lines.append(f"Location: {profile_data['location'] or 'Not provided'}")
    lines.append(f"Target Role: {profile_data['target_role'] or 'Not specified'}")

    lines.append("\n--- SKILLS ---")
    for s in profile_data['skills']:
        lines.append(f"- {s['name']} ({s['level']})")
    if not profile_data['skills']:
        lines.append("(none)")

    lines.append("\n--- EDUCATION ---")
    for e in profile_data['education']:
        parts = [e['degree'], e['field'], f"at {e['institution']}"]
        if e['graduation_year']:
            parts.append(f"({e['graduation_year']})")
        if e['cgpa']:
            parts.append(f"CGPA: {e['cgpa']}")
        lines.append(f"- {' - '.join(filter(None, parts))}")
    if not profile_data['education']:
        lines.append("(none)")

    lines.append("\n--- EXPERIENCE ---")
    for exp in profile_data['experience']:
        lines.append(f"- {exp['role']} at {exp['company']} ({exp['start_date']} - {exp['end_date']})")
        if exp['description']:
            lines.append(f"  Description: {exp['description']}")
        if exp['technologies']:
            lines.append(f"  Technologies: {', '.join(exp['technologies'])}")
    if not profile_data['experience']:
        lines.append("(none)")

    lines.append("\n--- PROJECTS ---")
    for p in profile_data['projects']:
        lines.append(f"- {p['name']}: {p['description']}")
        if p['technologies']:
            lines.append(f"  Technologies: {', '.join(p['technologies'])}")
    if not profile_data['projects']:
        lines.append("(none)")

    lines.append("\n--- CERTIFICATES ---")
    for c in profile_data['certificates']:
        parts = filter(None, [c['name'], c['issuer'], c['date']])
        lines.append(f"- {' - '.join(parts)}")
    if not profile_data['certificates']:
        lines.append("(none)")

    lines.append("\n--- LANGUAGES ---")
    for lang in profile_data['languages']:
        lines.append(f"- {lang['name']} ({lang['proficiency']})")
    if not profile_data['languages']:
        lines.append("(none)")

    lines.append("\n--- CURRENT SUMMARY ---")
    lines.append(profile_data['summary'] or "(none)")

    return "\n".join(lines)


GENERATION_SYSTEM_PROMPT = """You are an expert resume writer and career coach. Generate a complete, professional resume from the user's career profile data.

Rules:
1. Use the profile data factually — do NOT fabricate skills, experience, or credentials.
2. Improve wording, bullet points, readability, and impact — write like a senior resume writer would.
3. Generate 3-4 strong achievement-oriented bullet points for each experience entry.
4. Generate a compelling professional summary (2-3 sentences) that highlights the user's strengths and career trajectory.
5. Format projects with clear descriptions and technology tags.
6. Organize skills into meaningful groups if possible.
7. Keep the tone professional and ATS-friendly.
8. Each bullet point should start with a strong action verb and include measurable impact where possible.

Respond ONLY with valid JSON matching this structure:
{
  "summary": "Professional summary paragraph",
  "experience": [
    {
      "company": "...",
      "role": "...",
      "start": "...",
      "end": "...",
      "bullets": ["Achievement bullet 1", "Achievement bullet 2", "Achievement bullet 3"],
      "technologies": ["tech1", "tech2"]
    }
  ],
  "education": [
    {
      "school": "...",
      "degree": "...",
      "field": "...",
      "start": "",
      "end": "",
      "gpa": ""
    }
  ],
  "projects": [
    {
      "name": "...",
      "description": "...",
      "technologies": ["tech1", "tech2"],
      "url": ""
    }
  ],
  "skills": ["Skill1", "Skill2", "Skill3"],
  "certificates": [
    {"name": "...", "issuer": "...", "date": ""}
  ],
  "languages": [
    {"name": "...", "level": "..."}
  ]
}

Do not include any text outside the JSON object."""


def generate_resume(user_id, target_role=None, job_description=None):
    """Generate a complete AI-improved resume from the user's career profile."""
    profile_data = _collect_profile_data(user_id)
    if target_role:
        profile_data["target_role"] = target_role

    prompt = _profile_to_prompt(profile_data)
    if job_description:
        prompt += f"\n\n--- TARGET JOB DESCRIPTION ---\n{job_description}\n\nTailor the resume to this job description."

    from app.ai_service import generate_text

    system = GENERATION_SYSTEM_PROMPT
    raw = generate_text(prompt, model="gemini", system_instruction=system)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1] if len(parts) > 1 else cleaned
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]

    try:
        resume_data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("AI resume generation returned invalid JSON: %s", raw[:500])
        resume_data = _fallback_resume(profile_data)

    resume_data["full_name"] = profile_data["full_name"]
    resume_data["email"] = profile_data["email"]
    resume_data["phone"] = profile_data["phone"]
    resume_data["location"] = profile_data["location"]
    resume_data["title"] = profile_data["target_role"]

    return resume_data


def _fallback_resume(profile_data):
    """Build a simple resume from profile data if AI fails."""
    skills = [s["name"] for s in profile_data["skills"]]
    experience = []
    for exp in profile_data["experience"]:
        experience.append({
            "company": exp["company"],
            "role": exp["role"],
            "start": exp["start_date"],
            "end": exp["end_date"],
            "bullets": [exp["description"]] if exp["description"] else [""],
            "technologies": exp["technologies"],
        })
    education = []
    for edu in profile_data["education"]:
        education.append({
            "school": edu["institution"],
            "degree": edu["degree"],
            "field": edu["field"],
            "start": "",
            "end": str(edu["graduation_year"]) if edu["graduation_year"] else "",
            "gpa": str(edu["cgpa"]) if edu["cgpa"] else "",
        })
    projects = []
    for p in profile_data["projects"]:
        projects.append({
            "name": p["name"],
            "description": p["description"],
            "technologies": p["technologies"],
            "url": p["url"],
        })
    certificates = [{"name": c["name"], "issuer": c["issuer"], "date": c["date"]} for c in profile_data["certificates"]]
    languages = [{"name": lang["name"], "level": lang["proficiency"]} for lang in profile_data["languages"]]

    return {
        "summary": profile_data["summary"] or "",
        "experience": experience,
        "education": education,
        "projects": projects,
        "skills": skills,
        "certificates": certificates,
        "languages": languages,
    }


def generate_tailored_resume(user_id, source_version_id, job_description):
    """Create a tailored version of an existing resume for a specific job."""
    from app.resume.models import ResumeVersion

    source = ResumeVersion.query.get(source_version_id)
    if not source:
        return None

    profile_data = _collect_profile_data(user_id)
    snapshot = source.snapshot or {}

    prompt = f"""Original Resume:
{json.dumps(snapshot, indent=2)}

Target Job Description:
{job_description}

Career Profile Skills: {', '.join(s["name"] for s in profile_data["skills"])}

Create a tailored version of this resume optimized for the target job.
- Incorporate relevant keywords from the job description
- Highlight matching experience and skills
- Rephrase bullets to emphasize relevant achievements
- Keep all factual information accurate
- NEVER fabricate experience or skills not in the original resume

Respond with the same JSON structure as the original resume."""

    from app.ai_service import generate_text

    system = """You are an ATS optimization expert. Tailor the resume to maximize keyword matching while keeping all facts accurate.
Respond ONLY with valid JSON matching the original resume structure. Do not include any text outside the JSON."""

    raw = generate_text(prompt, model="gemini", system_instruction=system)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1] if len(parts) > 1 else cleaned
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]

    try:
        tailored = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("AI tailoring returned invalid JSON: %s", raw[:500])
        tailored = dict(snapshot)

    for field in ["full_name", "email", "phone", "location", "title"]:
        if field in snapshot:
            tailored[field] = snapshot[field]

    return tailored


def improve_section(text, section_type, tone="professional"):
    """AI-improve a single resume section."""
    from app.ai_service import generate_text

    prompts = {
        "summary": f"Rewrite this professional summary to be more impactful and ATS-friendly: \"{text}\"\nTone: {tone}\nReturn ONLY the rewritten text.",
        "bullet": f"Rewrite this resume bullet point to be more impactful with strong action verbs and metrics: \"{text}\"\nTone: {tone}\nReturn ONLY the rewritten bullet point.",
        "project": f"Improve this project description to highlight technical achievements and impact: \"{text}\"\nTone: {tone}\nReturn ONLY the improved description.",
        "achievement": f"Rewrite this as a measurable achievement: \"{text}\"\nTone: {tone}\nReturn ONLY the rewritten text.",
    }

    system = {
        "summary": "You are an expert resume writer. Strengthen professional summaries for ATS and impact.",
        "bullet": "You are an expert resume coach. Transform weak bullet points into powerful, metric-driven achievements.",
        "project": "You are a technical writer. Improve project descriptions to highlight engineering impact.",
        "achievement": "You are a career coach. Turn responsibilities into measurable achievements.",
    }

    instruction = prompts.get(section_type, prompts["bullet"])
    system_text = system.get(section_type, system["bullet"])

    raw = generate_text(instruction, model="gemini", system_instruction=system_text)
    return raw.strip()
