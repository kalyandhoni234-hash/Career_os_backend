import logging
from datetime import datetime, timezone
from typing import Optional

from app.extensions import db
from app.core.session import safe_commit
from app.knowledge.models import InterviewRecord

logger = logging.getLogger(__name__)


def list_interviews(
    user_id: int,
    opportunity_id: Optional[int] = None,
    company: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    q = InterviewRecord.query.filter_by(user_id=user_id)
    if opportunity_id:
        q = q.filter_by(opportunity_id=opportunity_id)
    if company:
        q = q.filter(InterviewRecord.company.ilike(f"%{company}%"))
    total = q.count()
    records = q.order_by(InterviewRecord.date.desc().nullslast()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()
    return {
        "interviews": [_record_to_dict(r) for r in records],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def get_interview(user_id: int, interview_id: int) -> Optional[dict]:
    r = InterviewRecord.query.filter_by(id=interview_id, user_id=user_id).first()
    return _record_to_dict(r) if r else None


def create_interview(user_id: int, data: dict) -> dict:
    record = InterviewRecord(
        user_id=user_id,
        opportunity_id=data.get("opportunity_id"),
        company=data.get("company", ""),
        role=data.get("role", ""),
        interview_type=data.get("interview_type", "technical"),
        round=data.get("round", 1),
        date=datetime.fromisoformat(data["date"]) if data.get("date") else None,
        questions_asked=data.get("questions_asked", []),
        answers_given=data.get("answers_given", []),
        feedback=data.get("feedback"),
        mistakes=data.get("mistakes", []),
        coding_problems=data.get("coding_problems", []),
        behavioral_questions=data.get("behavioral_questions", []),
        lessons_learned=data.get("lessons_learned"),
        resources=data.get("resources", []),
        tags=data.get("tags", []),
        difficulty_rating=data.get("difficulty_rating", 3),
        offer_received=data.get("offer_received", False),
        notes=data.get("notes"),
    )
    db.session.add(record)
    safe_commit()
    return _record_to_dict(record)


def update_interview(user_id: int, interview_id: int, data: dict) -> Optional[dict]:
    record = InterviewRecord.query.filter_by(
        id=interview_id, user_id=user_id
    ).first()
    if not record:
        return None
    for field in (
        "company",
        "role",
        "interview_type",
        "round",
        "questions_asked",
        "answers_given",
        "feedback",
        "mistakes",
        "coding_problems",
        "behavioral_questions",
        "lessons_learned",
        "resources",
        "tags",
        "difficulty_rating",
        "offer_received",
        "notes",
    ):
        if field in data:
            setattr(record, field, data[field])
    if data.get("date"):
        record.date = datetime.fromisoformat(data["date"])
    safe_commit()
    return _record_to_dict(record)


def delete_interview(user_id: int, interview_id: int) -> bool:
    record = InterviewRecord.query.filter_by(
        id=interview_id, user_id=user_id
    ).first()
    if not record:
        return False
    db.session.delete(record)
    safe_commit()
    return True


def get_topics_by_company(user_id: int) -> list[dict]:
    records = InterviewRecord.query.filter_by(user_id=user_id).all()
    company_topics: dict[str, set[str]] = {}
    for r in records:
        if r.company not in company_topics:
            company_topics[r.company] = set()
        for q in r.questions_asked or []:
            if isinstance(q, str):
                company_topics[r.company].add(q)
        for cp in r.coding_problems or []:
            if isinstance(cp, str):
                company_topics[r.company].add(cp)
    return [
        {"company": company, "topics": sorted(topics)}
        for company, topics in company_topics.items()
    ]


def get_interview_stats(user_id: int) -> dict:
    records = InterviewRecord.query.filter_by(user_id=user_id).all()
    total = len(records)
    if total == 0:
        return {"total_interviews": 0, "offers": 0, "conversion_rate": 0}

    offers = sum(1 for r in records if r.offer_received)
    companies = {r.company for r in records}
    avg_difficulty = (
        round(sum(r.difficulty_rating for r in records) / total) if total else 0
    )
    all_tags: list[str] = []
    for r in records:
        all_tags.extend(r.tags or [])
    tag_freq = {}
    for t in all_tags:
        tag_freq[t] = tag_freq.get(t, 0) + 1

    return {
        "total_interviews": total,
        "offers": offers,
        "conversion_rate": round(offers / max(total, 1) * 100),
        "unique_companies": len(companies),
        "avg_difficulty": avg_difficulty,
        "common_tags": sorted(tag_freq.items(), key=lambda x: -x[1])[:15],
    }


def _record_to_dict(r: InterviewRecord) -> dict:
    if not r:
        return None
    return {
        "id": r.id,
        "opportunity_id": r.opportunity_id,
        "company": r.company,
        "role": r.role,
        "interview_type": r.interview_type,
        "round": r.round,
        "date": r.date.isoformat() if r.date else None,
        "questions_asked": r.questions_asked or [],
        "answers_given": r.answers_given or [],
        "feedback": r.feedback,
        "mistakes": r.mistakes or [],
        "coding_problems": r.coding_problems or [],
        "behavioral_questions": r.behavioral_questions or [],
        "lessons_learned": r.lessons_learned,
        "resources": r.resources or [],
        "tags": r.tags or [],
        "difficulty_rating": r.difficulty_rating,
        "offer_received": r.offer_received,
        "notes": r.notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
