from datetime import datetime, timezone
from app.extensions import db


class Contact(db.Model):
    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=True
    )
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=True)
    company = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    relationship = db.Column(
        db.String(50), default="contact"
    )
    notes = db.Column(db.Text, nullable=True)
    last_contacted_at = db.Column(db.DateTime, nullable=True)
    next_follow_up_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default="active")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("contacts", lazy="dynamic"))
    opportunity = db.relationship(
        "Opportunity", backref=db.backref("contacts", lazy="dynamic")
    )


class Interaction(db.Model):
    __tablename__ = "contact_interactions"

    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(
        db.Integer, db.ForeignKey("contacts.id"), nullable=False
    )
    interaction_type = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    outcome = db.Column(db.String(255), nullable=True)
    occurred_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    contact = db.relationship(
        "Contact", backref=db.backref("interactions", lazy="dynamic", cascade="all, delete-orphan")
    )
