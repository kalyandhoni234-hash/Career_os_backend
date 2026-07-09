from datetime import datetime, timezone
from app.extensions import db

class Recruiter(db.Model):
    __tablename__ = "recruiters"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)
    full_name = db.Column(db.String(255))
    title = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    linkedin = db.Column(db.String(500))
    department = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("recruiter", uselist=False))

class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    website = db.Column(db.String(500))
    logo_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    industry = db.Column(db.String(255))
    headquarters = db.Column(db.String(255))
    company_size = db.Column(db.String(100))
    founded_year = db.Column(db.Integer)
    linkedin_url = db.Column(db.String(500))
    twitter_url = db.Column(db.String(500))
    culture_description = db.Column(db.Text)
    benefits_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    job_posts = db.relationship("JobPost", backref="company", lazy="dynamic")

class JobPost(db.Model):
    __tablename__ = "job_posts"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(255))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    salary_currency = db.Column(db.String(10), default="USD")
    experience_required = db.Column(db.String(50))
    experience_max = db.Column(db.String(50))
    employment_type = db.Column(db.String(50))
    skills_required = db.Column(db.JSON)
    benefits = db.Column(db.JSON)
    application_deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default="active")
    is_remote = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    recruiter = db.relationship("Recruiter", backref=db.backref("job_posts", lazy="dynamic"))

class SavedCandidate(db.Model):
    __tablename__ = "saved_candidates"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pipeline_id = db.Column(db.Integer, db.ForeignKey("talent_pipelines.id"), nullable=True)
    notes = db.Column(db.Text)
    rating = db.Column(db.Integer)
    status = db.Column(db.String(50), default="saved")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    recruiter = db.relationship("Recruiter", backref=db.backref("saved_candidates", lazy="dynamic"))
    candidate = db.relationship("User", foreign_keys=[candidate_id])
    pipeline = db.relationship("TalentPipeline", backref=db.backref("saved_candidates", lazy="dynamic"))

    __table_args__ = (db.UniqueConstraint("recruiter_id", "candidate_id"),)

class TalentPipeline(db.Model):
    __tablename__ = "talent_pipelines"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    recruiter = db.relationship("Recruiter", backref=db.backref("talent_pipelines", lazy="dynamic"))

    __table_args__ = (db.UniqueConstraint("recruiter_id", "name"),)

class CandidateView(db.Model):
    __tablename__ = "candidate_views"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    source = db.Column(db.String(50))
    viewed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    recruiter = db.relationship("Recruiter", backref=db.backref("candidate_views", lazy="dynamic"))
    candidate = db.relationship("User", foreign_keys=[candidate_id])

class InterviewInvite(db.Model):
    __tablename__ = "interview_invites"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_post_id = db.Column(db.Integer, db.ForeignKey("job_posts.id"), nullable=True)
    message = db.Column(db.Text)
    interview_type = db.Column(db.String(50))
    scheduled_date = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer)
    location = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    responded_at = db.Column(db.DateTime)

    recruiter = db.relationship("Recruiter", backref=db.backref("interview_invites", lazy="dynamic"))
    candidate = db.relationship("User", foreign_keys=[candidate_id])
    job_post = db.relationship("JobPost", backref=db.backref("interview_invites", lazy="dynamic"))

class RecruiterNotification(db.Model):
    __tablename__ = "recruiter_notifications"

    id = db.Column(db.Integer, primary_key=True)
    recruiter_id = db.Column(db.Integer, db.ForeignKey("recruiters.id"), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    data = db.Column(db.JSON)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    recruiter = db.relationship("Recruiter", backref=db.backref("notifications", lazy="dynamic"))
