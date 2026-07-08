from flask import Blueprint, request, jsonify, make_response
from flask_login import login_required, current_user
from app.extensions import db
from app.resume.models import Resume

resume_bp = Blueprint("resume", __name__)

@resume_bp.route("/ping")
def ping():
    return {"blueprint": "resume", "status": "alive"}

@resume_bp.route("", methods=["GET"])
@login_required
def get_resume():
    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        return jsonify({"resume": None}), 200

    return jsonify({
        "resume": {
            "id": resume.id,
            "full_name": resume.full_name,
            "email": resume.email,
            "phone": resume.phone,
            "location": resume.location,
            "summary": resume.summary,
            "experience": resume.experience,
            "education": resume.education,
            "projects": resume.projects,
            "skills": resume.skills,
        }
    }), 200

@resume_bp.route("", methods=["POST", "PUT"])
@login_required
def upsert_resume():
    data = request.get_json(silent=True) or {}

    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        resume = Resume(user_id=current_user.id)
        db.session.add(resume)

    resume.full_name = data.get("full_name", resume.full_name)
    resume.email = data.get("email", resume.email)
    resume.phone = data.get("phone", resume.phone)
    resume.location = data.get("location", resume.location)
    resume.summary = data.get("summary", resume.summary)
    resume.experience = data.get("experience", resume.experience)
    resume.education = data.get("education", resume.education)
    resume.projects = data.get("projects", resume.projects)
    resume.skills = data.get("skills", resume.skills)

    db.session.commit()

    return jsonify({"message": "Resume saved successfully", "id": resume.id}), 200

def _escape(text):
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

@resume_bp.route("/export", methods=["GET"])
@login_required
def export_resume():
    from weasyprint import HTML

    resume = Resume.query.filter_by(user_id=current_user.id).first()
    if not resume:
        return jsonify({"error": "No resume found"}), 404

    experience_html = ""
    for exp in (resume.experience or []):
        bullets = exp.get("bullets", "") or ""
        bullet_items = "".join(f"<li>{_escape(b)}</li>" for b in bullets.split(chr(10)) if b.strip())
        experience_html += f"""
        <div class="entry">
            <div class="entry-header">
                <strong>{_escape(exp.get("role"))}</strong> - {_escape(exp.get("company"))}
                <span class="dates">{_escape(exp.get("start"))} - {_escape(exp.get("end"))}</span>
            </div>
            <ul>{bullet_items}</ul>
        </div>
        """

    education_html = ""
    for edu in (resume.education or []):
        education_html += f"""
        <div class="entry">
            <div class="entry-header">
                <strong>{_escape(edu.get("degree"))}</strong> - {_escape(edu.get("school"))}
                <span class="dates">{_escape(edu.get("start"))} - {_escape(edu.get("end"))}</span>
            </div>
        </div>
        """

    projects_html = ""
    for proj in (resume.projects or []):
        link_html = f" ({_escape(proj.get(chr(108)+chr(105)+chr(110)+chr(107)))})" if proj.get("link") else ""
        projects_html += f"""
        <div class="entry">
            <strong>{_escape(proj.get("name"))}</strong>{link_html}
            <p>{_escape(proj.get("description"))}</p>
        </div>
        """

    skills_html = ", ".join(_escape(s) for s in (resume.skills or []))

    html_content = f"""
    <html>
    <head><style>
        body {{ font-family: Arial, sans-serif; color: #222; margin: 40px; font-size: 13px; }}
        h1 {{ margin-bottom: 4px; font-size: 22px; }}
        .contact {{ color: #555; margin-bottom: 20px; font-size: 12px; }}
        h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 24px; font-size: 15px; }}
        .entry {{ margin-bottom: 14px; }}
        .entry-header {{ display: flex; justify-content: space-between; }}
        .dates {{ color: #666; font-size: 12px; }}
        ul {{ margin: 6px 0 0 18px; padding: 0; }}
        li {{ margin-bottom: 2px; }}
    </style></head>
    <body>
        <h1>{_escape(resume.full_name)}</h1>
        <div class="contact">{_escape(resume.email)} | {_escape(resume.phone)} | {_escape(resume.location)}</div>

        <h2>Summary</h2>
        <p>{_escape(resume.summary)}</p>

        <h2>Experience</h2>
        {experience_html or "<p>No experience added yet.</p>"}

        <h2>Education</h2>
        {education_html or "<p>No education added yet.</p>"}

        <h2>Projects</h2>
        {projects_html or "<p>No projects added yet.</p>"}

        <h2>Skills</h2>
        <p>{skills_html}</p>
    </body>
    </html>
    """

    pdf_bytes = HTML(string=html_content).write_pdf()
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=resume.pdf"
    return response

