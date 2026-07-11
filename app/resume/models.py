from datetime import datetime, timezone
from app.extensions import db


class ResumeVersion(db.Model):
    """Single source of truth for every resume snapshot.

    Covers both generic manual versions (v1, v2, ...) and versions
    auto-generated/tailored for a specific opportunity/company, which
    previously lived in the now-removed `ResumeVersionByCompany` model.
    `opportunity_id` / `company_name` / `ats_score` / `job_description_used`
    are populated only for opportunity-tailored versions and stay null
    for plain manual versions.
    """

    __tablename__ = "resume_versions"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    version_name = db.Column(db.String(100), nullable=False, default="v1")
    snapshot = db.Column(db.JSON, nullable=False)

    # Fields specific to opportunity-tailored versions (nullable).
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=True
    )
    company_name = db.Column(db.String(255), nullable=True)
    ats_score = db.Column(db.Integer, nullable=True)
    job_description_used = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    opportunity = db.relationship(
        "Opportunity", backref=db.backref("resume_versions", lazy="dynamic")
    )


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    full_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    location = db.Column(db.String(255))
    summary = db.Column(db.Text)
    title = db.Column(db.String(255))
    website = db.Column(db.String(500))
    linkedin = db.Column(db.String(500))
    github = db.Column(db.String(500))
    portfolio = db.Column(db.String(500))

    experience = db.Column(db.JSON)
    education = db.Column(db.JSON)
    projects = db.Column(db.JSON)
    skills = db.Column(db.JSON)
    certificates = db.Column(db.JSON)
    achievements = db.Column(db.JSON)
    languages = db.Column(db.JSON)
    publications = db.Column(db.JSON)

    target_job_description = db.Column(db.Text)
    tone = db.Column(db.String(50), default="professional")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    versions = db.relationship(
        "ResumeVersion", backref="resume", lazy="dynamic", cascade="all, delete-orphan"
    )


class ResumeFile(db.Model):
    """Metadata for a raw uploaded resume file (PDF/DOCX) used for import.

    Distinct concern from `Resume` (the structured, editable resume content):
    this tracks the original uploaded artifact. `resume_id` links it to the
    structured `Resume` row it was parsed into, once import completes.
    Relocated here from app/career/models.py so all resume-related models
    live in one module instead of being split across two blueprints.
    """

    __tablename__ = "resume_files"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    file_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", backref=db.backref("resume_files", lazy="dynamic"))
    parsed_resume = db.relationship(
        "Resume", backref=db.backref("source_files", lazy="dynamic")
    )
