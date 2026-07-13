from datetime import datetime, timezone
from app.extensions import db


class InterviewRecord(db.Model):
    __tablename__ = "interview_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=True
    )
    company = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=False)
    interview_type = db.Column(db.String(50), default="technical")
    round = db.Column(db.Integer, default=1)
    date = db.Column(db.DateTime, nullable=True)
    questions_asked = db.Column(db.JSON, default=list)
    answers_given = db.Column(db.JSON, default=list)
    feedback = db.Column(db.Text, nullable=True)
    mistakes = db.Column(db.JSON, default=list)
    coding_problems = db.Column(db.JSON, default=list)
    behavioral_questions = db.Column(db.JSON, default=list)
    lessons_learned = db.Column(db.Text, nullable=True)
    resources = db.Column(db.JSON, default=list)
    tags = db.Column(db.JSON, default=list)
    difficulty_rating = db.Column(db.Integer, default=3)
    offer_received = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "User", backref=db.backref("interview_records", lazy="dynamic")
    )
    opportunity = db.relationship(
        "Opportunity", backref=db.backref("interview_records", lazy="dynamic")
    )
