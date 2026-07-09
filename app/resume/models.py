from datetime import datetime
from app.extensions import db


class ResumeVersion(db.Model):
    __tablename__ = "resume_versions"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False)
    version_name = db.Column(db.String(100), nullable=False, default="v1")
    snapshot = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = db.relationship("ResumeVersion", backref="resume", lazy="dynamic", cascade="all, delete-orphan")
