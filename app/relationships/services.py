import logging
from datetime import datetime, timezone
from typing import Optional

from app.extensions import db
from app.core.session import safe_commit
from app.relationships.models import Contact, Interaction

logger = logging.getLogger(__name__)

RELATIONSHIP_TYPES = [
    "recruiter",
    "hiring_manager",
    "referral",
    "alumni",
    "mentor",
    "friend",
    "linkedin_connection",
    "colleague",
    "other",
]


def list_contacts(
    user_id: int,
    opportunity_id: Optional[int] = None,
    relationship: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    q = Contact.query.filter_by(user_id=user_id)
    if opportunity_id:
        q = q.filter_by(opportunity_id=opportunity_id)
    if relationship:
        q = q.filter_by(relationship=relationship)
    if status:
        q = q.filter_by(status=status)
    total = q.count()
    contacts = q.order_by(Contact.updated_at.desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    return {
        "contacts": [_contact_to_dict(c) for c in contacts],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def get_contact(user_id: int, contact_id: int) -> Optional[dict]:
    c = Contact.query.filter_by(id=contact_id, user_id=user_id).first()
    if not c:
        return None
    result = _contact_to_dict(c)
    result["interactions"] = [
        _interaction_to_dict(i)
        for i in c.interactions.order_by(Interaction.occurred_at.desc()).all()
    ]
    return result


def create_contact(user_id: int, data: dict) -> dict:
    contact = Contact(
        user_id=user_id,
        opportunity_id=data.get("opportunity_id"),
        name=data.get("name", ""),
        role=data.get("role"),
        company=data.get("company"),
        email=data.get("email"),
        linkedin_url=data.get("linkedin_url"),
        phone=data.get("phone"),
        relationship=data.get("relationship", "contact"),
        notes=data.get("notes"),
        status=data.get("status", "active"),
    )
    db.session.add(contact)
    safe_commit()
    return _contact_to_dict(contact)


def update_contact(user_id: int, contact_id: int, data: dict) -> Optional[dict]:
    contact = Contact.query.filter_by(id=contact_id, user_id=user_id).first()
    if not contact:
        return None
    for field in (
        "name",
        "role",
        "company",
        "email",
        "linkedin_url",
        "phone",
        "relationship",
        "notes",
        "status",
        "next_follow_up_at",
    ):
        if field in data:
            setattr(contact, field, data[field])
    safe_commit()
    return _contact_to_dict(contact)


def delete_contact(user_id: int, contact_id: int) -> bool:
    contact = Contact.query.filter_by(id=contact_id, user_id=user_id).first()
    if not contact:
        return False
    db.session.delete(contact)
    safe_commit()
    return True


def log_interaction(user_id: int, contact_id: int, data: dict) -> Optional[dict]:
    contact = Contact.query.filter_by(id=contact_id, user_id=user_id).first()
    if not contact:
        return None
    interaction = Interaction(
        contact_id=contact_id,
        interaction_type=data.get("interaction_type", "note"),
        notes=data.get("notes"),
        outcome=data.get("outcome"),
        occurred_at=datetime.fromisoformat(data["occurred_at"]) if data.get("occurred_at") else datetime.now(timezone.utc),
    )
    contact.last_contacted_at = interaction.occurred_at
    db.session.add(interaction)
    safe_commit()
    return _interaction_to_dict(interaction)


def get_networking_health(user_id: int) -> dict:
    contacts = Contact.query.filter_by(user_id=user_id).all()
    total = len(contacts)
    if total == 0:
        return {"health_score": 0, "total_contacts": 0, "breakdown": {}}

    active = sum(1 for c in contacts if c.status == "active")
    with_linkedin = sum(1 for c in contacts if c.linkedin_url)
    contacted_recently = sum(
        1
        for c in contacts
        if c.last_contacted_at
        and (datetime.now(timezone.utc) - c.last_contacted_at).days < 30
    )
    with_upcoming = sum(1 for c in contacts if c.next_follow_up_at)
    relationship_diversity = len({c.relationship for c in contacts if c.relationship})

    score = min(
        100,
        int(
            (active / max(total, 1)) * 25
            + (with_linkedin / max(total, 1)) * 15
            + (contacted_recently / max(total, 1)) * 25
            + (with_upcoming / max(total, 1)) * 15
            + min(relationship_diversity * 5, 20)
        ),
    )

    return {
        "health_score": score,
        "total_contacts": total,
        "active_contacts": active,
        "contacted_recently": contacted_recently,
        "with_upcoming_follow_up": with_upcoming,
        "relationship_diversity": relationship_diversity,
        "breakdown": {
            "active_ratio": round(active / max(total, 1) * 100),
            "linkedin_presence": round(with_linkedin / max(total, 1) * 100),
            "recent_contact_ratio": round(contacted_recently / max(total, 1) * 100),
            "follow_up_ratio": round(with_upcoming / max(total, 1) * 100),
        },
    }


def get_due_follow_ups(user_id: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    contacts = (
        Contact.query.filter(
            Contact.user_id == user_id,
            Contact.next_follow_up_at.isnot(None),
            Contact.next_follow_up_at <= now,
        )
        .order_by(Contact.next_follow_up_at.asc())
        .all()
    )
    return [_contact_to_dict(c) for c in contacts]


def _contact_to_dict(c: Contact) -> dict:
    return {
        "id": c.id,
        "opportunity_id": c.opportunity_id,
        "name": c.name,
        "role": c.role,
        "company": c.company,
        "email": c.email,
        "linkedin_url": c.linkedin_url,
        "phone": c.phone,
        "relationship": c.relationship,
        "notes": c.notes,
        "last_contacted_at": c.last_contacted_at.isoformat() if c.last_contacted_at else None,
        "next_follow_up_at": c.next_follow_up_at.isoformat() if c.next_follow_up_at else None,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _interaction_to_dict(i: Interaction) -> dict:
    return {
        "id": i.id,
        "interaction_type": i.interaction_type,
        "notes": i.notes,
        "outcome": i.outcome,
        "occurred_at": i.occurred_at.isoformat() if i.occurred_at else None,
    }
