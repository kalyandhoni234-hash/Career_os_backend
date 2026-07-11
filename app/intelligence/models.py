from datetime import datetime, timezone
from app.extensions import db


class CanonicalProject(db.Model):
    __tablename__ = "canonical_projects"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(500), nullable=True)
    repo_url = db.Column(db.String(500), nullable=True)
    primary_language = db.Column(db.String(100), nullable=True)
    languages = db.Column(db.JSON, default=list)
    stars = db.Column(db.Integer, default=0)
    is_pinned = db.Column(db.Boolean, default=False)
    is_fork = db.Column(db.Boolean, default=False)
    topics = db.Column(db.JSON, default=list)
    readme_url = db.Column(db.String(500), nullable=True)

    source = db.Column(db.String(50), default="manual")
    source_id = db.Column(db.String(255), nullable=True)
    confidence = db.Column(db.Float, default=1.0)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("canonical_projects", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "source", "source_id", name="uq_project_source"),
    )


class CanonicalExperience(db.Model):
    __tablename__ = "canonical_experience"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    company = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.String(20), nullable=True)
    end_date = db.Column(db.String(20), nullable=True)
    is_current = db.Column(db.Boolean, default=False)
    employment_type = db.Column(db.String(50), nullable=True)
    technologies = db.Column(db.JSON, default=list)

    source = db.Column(db.String(50), default="manual")
    source_id = db.Column(db.String(255), nullable=True)
    confidence = db.Column(db.Float, default=1.0)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("canonical_experience", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "source", "source_id", name="uq_experience_source"),
    )


class CanonicalCertificate(db.Model):
    __tablename__ = "canonical_certificates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(255), nullable=False)
    issuer = db.Column(db.String(255), nullable=True)
    url = db.Column(db.String(500), nullable=True)
    issue_date = db.Column(db.String(20), nullable=True)
    expiry_date = db.Column(db.String(20), nullable=True)
    credential_id = db.Column(db.String(255), nullable=True)

    source = db.Column(db.String(50), default="manual")
    source_id = db.Column(db.String(255), nullable=True)
    confidence = db.Column(db.Float, default=1.0)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("canonical_certificates", lazy="dynamic"))


class CareerEvent(db.Model):
    __tablename__ = "career_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    event_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_source = db.Column(db.String(50), default="manual")
    source_id = db.Column(db.String(255), nullable=True)
    occurred_at = db.Column(db.DateTime, nullable=True)

    metadata_json = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("career_events", lazy="dynamic"))
