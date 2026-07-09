from datetime import datetime
from app.extensions import db

class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    company = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="applied")
    # status values: applied, oa, interview, offer, rejected

    salary = db.Column(db.String(100))
    recruiter = db.Column(db.String(255))
    notes = db.Column(db.Text)
    deadline = db.Column(db.Date)
    job_link = db.Column(db.String(500))

    priority = db.Column(db.String(20), default="medium")
    # priority values: low, medium, high

    next_action = db.Column(db.String(255))
    resume_version = db.Column(db.String(50))
    ats_score = db.Column(db.Integer)
    location = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
