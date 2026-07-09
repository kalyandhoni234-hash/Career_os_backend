import json
import logging
from app.extensions import db
from app.opportunities.models import Opportunity, ResumeVersionByCompany, InterviewPack
from app.ai_service import generate_text

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are an expert career strategist and resume writer. Return only valid JSON without markdown formatting."


def generate_optimized_resume(user_id: int, opportunity_id: int) -> dict:
    from app.resume.models import Resume

    opp = Opportunity.query.get(opportunity_id)
    resume = Resume.query.filter_by(user_id=user_id).first()
    if not opp or not resume:
        return {"error": "Opportunity or resume not found"}

    existing = ResumeVersionByCompany.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).order_by(ResumeVersionByCompany.created_at.desc()).first()
    if existing:
        return _version_to_dict(existing)

    description_text = f"{opp.description or ''}\nRequirements: {' '.join(opp.requirements or [])}\nResponsibilities: {' '.join(opp.responsibilities or [])}"

    resume_json = {
        "full_name": resume.full_name,
        "email": resume.email,
        "phone": resume.phone,
        "summary": resume.summary,
        "experience": resume.experience or [],
        "education": resume.education or [],
        "skills": resume.skills or [],
        "projects": resume.projects or [],
        "certificates": resume.certificates or [],
    }

    prompt = f"""Given this job description:
{description_text}

And this current resume:
{json.dumps(resume_json, indent=2)}

Generate an optimized version of this resume tailored specifically for this job. Return a JSON object with:
1. "optimized_summary": A rewritten professional summary targeting this specific role
2. "added_keywords": List of keywords from the job description that were added
3. "skill_additions": List of skills from the job that should be emphasized
4. "suggested_experience_rewrites": Array of objects with "index" and "bullets" - rewritten bullet points for relevant experience
5. "ats_improvement_estimate": Estimated ATS score improvement (0-100)

Return ONLY valid JSON."""

    try:
        result_text = generate_text(prompt, model="gemini", system_instruction=SYSTEM_PROMPT)
        result_text = result_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        result = json.loads(result_text)
    except Exception as e:
        logger.warning("AI resume optimization failed, using fallback: %s", e)
        result = _fallback_optimization(resume_json, description_text)

    version = ResumeVersionByCompany(
        user_id=user_id,
        opportunity_id=opportunity_id,
        company_name=opp.company_name,
        version_name=opp.title[:100],
        resume_json=resume_json,
        job_description_used=description_text,
    )
    db.session.add(version)
    db.session.commit()

    return {
        "version_id": version.id,
        "optimized_summary": result.get("optimized_summary", resume.summary),
        "added_keywords": result.get("added_keywords", []),
        "skill_additions": result.get("skill_additions", []),
        "suggested_experience_rewrites": result.get("suggested_experience_rewrites", []),
        "ats_improvement_estimate": result.get("ats_improvement_estimate", 60),
        "company_name": opp.company_name,
        "role": opp.title,
    }


def generate_cover_letter(user_id: int, opportunity_id: int, tone: str = "professional") -> dict:
    opp = Opportunity.query.get(opportunity_id)
    from app.resume.models import Resume
    resume = Resume.query.filter_by(user_id=user_id).first()

    if not opp or not resume:
        return {"error": "Opportunity or resume not found"}

    name = resume.full_name or "Candidate"
    company = opp.company_name
    role = opp.title
    location = opp.location or ""
    skills = ", ".join((resume.skills or [])[:10])
    experience_summary = ""
    if resume.experience:
        exp = resume.experience[0]
        experience_summary = f"{exp.get('role', '')} at {exp.get('company', '')}"

    email = resume.email or ""

    prompt = f"""Write a professional cover letter for:

Applicant: {name}
Email: {email}
Current Role: {experience_summary}
Key Skills: {skills}

Job: {role}
Company: {company}
Location: {location}

Tone: {tone}

Write a compelling, personalized cover letter (3-4 paragraphs) that connects the candidate's experience to the company's needs. Be specific and avoid generic statements.

Return JSON: {{"subject": "...", "body": "...", "salutation": "...", "closing": "..."}}"""

    try:
        result_text = generate_text(prompt, model="gemini", system_instruction=SYSTEM_PROMPT)
        result_text = result_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        result = json.loads(result_text)
    except Exception:
        result = {
            "subject": f"Application for {role} at {company}",
            "body": f"Dear Hiring Manager at {company},\n\nI am excited to apply for the {role} position. With experience in {skills}, I am confident I can contribute to {company}'s success.\n\n{experience_summary}\n\nThank you for your consideration.\n\nBest regards,\n{name}",
            "salutation": f"Dear Hiring Manager at {company},",
            "closing": f"Best regards,\n{name}",
        }

    return result


def generate_email(user_id: int, opportunity_id: int, email_type: str = "application") -> dict:
    opp = Opportunity.query.get(opportunity_id)
    from app.resume.models import Resume
    resume = Resume.query.filter_by(user_id=user_id).first()
    name = resume.full_name if resume else "Candidate"
    company = opp.company_name if opp else "Company"
    role = opp.title if opp else "Role"

    prompt = f"""Write a {email_type} email for:
Name: {name}
Company: {company}
Role: {role}

Return JSON: {{"subject": "...", "body": "..."}}"""

    try:
        result_text = generate_text(prompt, model="gemini", system_instruction=SYSTEM_PROMPT)
        result_text = result_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        result = json.loads(result_text)
    except Exception:
        result = {
            "subject": f"Application for {role} at {company}",
            "body": f"Dear Team at {company},\n\nI am writing to express my interest in the {role} position...\n\nBest regards,\n{name}",
        }

    return result


def generate_linkedin_message(user_id: int, opportunity_id: int, message_type: str = "connection") -> dict:
    opp = Opportunity.query.get(opportunity_id)
    from app.resume.models import Resume
    resume = Resume.query.filter_by(user_id=user_id).first()
    name = resume.full_name if resume else "Candidate"
    company = opp.company_name if opp else "Company"
    role = opp.title if opp else "Role"

    prompt = f"""Write a LinkedIn {message_type} message for:
Name: {name}
Target Company: {company}
Target Role: {role}

Return JSON: {{"subject": "...", "body": "..."}}"""

    try:
        result_text = generate_text(prompt, model="gemini", system_instruction=SYSTEM_PROMPT)
        result_text = result_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        result = json.loads(result_text)
    except Exception:
        result = {
            "subject": f"Interest in {role} at {company}",
            "body": f"Hi there, I'm very interested in the {role} role at {company} and would love to connect!",
        }

    return result


def generate_interview_questions(user_id: int, opportunity_id: int) -> dict:
    opp = Opportunity.query.get(opportunity_id)
    if not opp:
        return {"error": "Opportunity not found"}

    existing = InterviewPack.query.filter_by(
        user_id=user_id, opportunity_id=opportunity_id
    ).first()
    if existing:
        return _interview_pack_to_dict(existing)

    description_text = f"{opp.description or ''}\nRequirements: {' '.join(opp.requirements or [])}\n{' '.join(opp.responsibilities or [])}"
    tech = ", ".join(opp.tech_stack or []) if opp.tech_stack else "General"

    prompt = f"""Generate a comprehensive interview preparation pack for:

Company: {opp.company_name}
Role: {opp.title}
Description: {description_text}
Tech Stack: {tech}

Return a JSON object with these exact keys:
- "likely_questions": Array of {{"question": "...", "category": "technical|behavioral|system_design", "difficulty": "easy|medium|hard", "preparation_tip": "..."}}
- "coding_topics": Array of {{"topic": "...", "importance": 1-5, "description": "..."}}
- "behavioral_questions": Array of {{"question": "...", "framework": "STAR", "key_points": ["..."]}}
- "system_design_topics": Array of {{"topic": "...", "importance": 1-5, "description": "..."}}
- "company_questions": Array of {{"question": "...", "context": "..."}}
- "preparation_checklist": Array of strings
- "learning_resources": Array of {{"topic": "...", "resource_type": "article|video|book|course", "description": "..."}}

Generate at least 5 items in each array where possible. Return ONLY valid JSON."""

    try:
        result_text = generate_text(prompt, model="gemini", system_instruction=SYSTEM_PROMPT)
        result_text = result_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
        result = json.loads(result_text)
    except Exception as e:
        logger.warning("AI interview question generation failed: %s", e)
        result = _fallback_interview_pack(opp)

    pack = InterviewPack(
        user_id=user_id,
        opportunity_id=opportunity_id,
        likely_questions=result.get("likely_questions", []),
        coding_topics=result.get("coding_topics", []),
        behavioral_questions=result.get("behavioral_questions", []),
        system_design_topics=result.get("system_design_topics", []),
        company_questions=result.get("company_questions", []),
        preparation_checklist=result.get("preparation_checklist", []),
        learning_resources=result.get("learning_resources", []),
    )
    db.session.add(pack)
    db.session.commit()

    return _interview_pack_to_dict(pack)


def _fallback_optimization(resume_json: dict, job_description: str) -> dict:
    return {
        "optimized_summary": resume_json.get("summary", ""),
        "added_keywords": [],
        "skill_additions": [],
        "suggested_experience_rewrites": [],
        "ats_improvement_estimate": 50,
    }


def _fallback_interview_pack(opp: Opportunity) -> dict:
    return {
        "likely_questions": [
            {"question": f"Tell me about your experience with {opp.tech_stack[0] if opp.tech_stack else 'relevant technologies'}", "category": "technical", "difficulty": "medium", "preparation_tip": "Prepare specific examples using this technology"},
            {"question": "Describe a challenging project and how you overcame obstacles", "category": "behavioral", "difficulty": "medium", "preparation_tip": "Use the STAR method"},
        ],
        "coding_topics": [{"topic": t, "importance": 4, "description": f"Core technology for {opp.company_name}"} for t in (opp.tech_stack or [])[:5]],
        "behavioral_questions": [
            {"question": "Why do you want to work at " + (opp.company_name or "our company") + "?", "framework": "STAR", "key_points": ["Research the company", "Connect your values"]},
            {"question": "Tell me about a time you handled a conflict", "framework": "STAR", "key_points": ["Be honest", "Focus on resolution"]},
        ],
        "system_design_topics": [{"topic": "System Design", "importance": 4, "description": "General system design principles"}],
        "company_questions": [{"question": f"What does the engineering culture look like at {opp.company_name}?", "context": "Team culture"}],
        "preparation_checklist": ["Research the company", "Review job description", "Prepare your questions", "Practice behavioral questions"],
        "learning_resources": [{"topic": t, "resource_type": "article", "description": f"Review {t} fundamentals"} for t in (opp.tech_stack or [])[:3]],
    }


def _version_to_dict(v: ResumeVersionByCompany) -> dict:
    return {
        "version_id": v.id,
        "company_name": v.company_name,
        "version_name": v.version_name,
        "ats_score": v.ats_score,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


def _interview_pack_to_dict(pack: InterviewPack) -> dict:
    return {
        "id": pack.id,
        "opportunity_id": pack.opportunity_id,
        "likely_questions": pack.likely_questions or [],
        "coding_topics": pack.coding_topics or [],
        "behavioral_questions": pack.behavioral_questions or [],
        "system_design_topics": pack.system_design_topics or [],
        "company_questions": pack.company_questions or [],
        "preparation_checklist": pack.preparation_checklist or [],
        "learning_resources": pack.learning_resources or [],
        "created_at": pack.created_at.isoformat() if pack.created_at else None,
    }
