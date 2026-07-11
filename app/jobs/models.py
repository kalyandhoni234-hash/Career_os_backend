from datetime import datetime
from app.extensions import db


class Job(db.Model):
    """Single source of truth for a user's job/internship applications.

    Whether an application originated from a manually-entered role or from
    discovering an `Opportunity` via the job matching module, its lifecycle
    (applied -> oa -> interview -> offer/rejected) lives here, and only here.
    `opportunity_id` is set when this application was created from a
    discovered Opportunity, so match score / skill gap data can be looked up
    without duplicating status/notes/deadline fields on SavedOpportunity.
    """

    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=True
    )

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
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    opportunity = db.relationship(
        "Opportunity", backref=db.backref("tracked_applications", lazy="dynamic")
    )
