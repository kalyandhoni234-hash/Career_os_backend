from datetime import datetime, timezone
from app.extensions import db


class Contact(db.Model):
    __tablename__ = "contacts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)

    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255))
    company = db.Column(db.String(255))
    email = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(500))
    phone = db.Column(db.String(50))

    # relationship type: recruiter, peer, mentor, alumni, other
    relationship = db.Column(db.String(50), default="other")
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default="active")  # active, inactive, pending

    last_contacted_at = db.Column(db.DateTime)
    next_follow_up_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    interactions = db.relationship("Interaction", backref="contact", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "name": self.name,
            "role": self.role,
            "company": self.company,
            "email": self.email,
            "linkedin_url": self.linkedin_url,
            "phone": self.phone,
            "relationship": self.relationship,
            "notes": self.notes,
            "status": self.status,
            "last_contacted_at": self.last_contacted_at.isoformat() if self.last_contacted_at else None,
            "next_follow_up_at": self.next_follow_up_at.isoformat() if self.next_follow_up_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Interaction(db.Model):
    __tablename__ = "contact_interactions"

    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)

    # email, linkedin, call, meeting, other
    interaction_type = db.Column(db.String(50), default="email")
    notes = db.Column(db.Text)
    outcome = db.Column(db.String(255))
    occurred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "interaction_type": self.interaction_type,
            "notes": self.notes,
            "outcome": self.outcome,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
