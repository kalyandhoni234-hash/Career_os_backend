from datetime import datetime, timezone
from app.extensions import db


class ResumeVersion(db.Model):
    """A resume version — can be AI-generated, tailored, or manually created."""

    __tablename__ = "resume_versions"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    version_name = db.Column(db.String(100), nullable=False, default="v1")
    target_role = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(50), default="manual")
    ats_score = db.Column(db.Integer, nullable=True)
    ats_data = db.Column(db.JSON, nullable=True)
    tailored_for_job = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    snapshot = db.Column(db.JSON, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
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

    @property
    def skills_list(self):
        raw = self.skills
        if not raw:
            return []
        if isinstance(raw, dict):
            flat = []
            for value in raw.values():
                if isinstance(value, list):
                    flat.extend(v for v in value if isinstance(v, str))
                elif isinstance(value, str):
                    flat.append(value)
            return flat
        if isinstance(raw, list):
            return [s for s in raw if isinstance(s, str)]
        return []
