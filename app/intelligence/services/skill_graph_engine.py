"""Skill Graph Engine — tracks every skill with multi-source confidence.

Skills are the atomic unit of Career OS. Every module contributes evidence
about what a user knows. This engine aggregates that evidence into a single
confidence score per skill and maintains the graph of related skills.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.extensions import db

logger = logging.getLogger(__name__)

SKILL_CATEGORIES: dict[str, list[str]] = {
    "languages": {
        "python", "javascript", "typescript", "java", "go", "rust", "c++", "c",
        "c#", "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "bash",
        "shell", "sql", "html", "css", "sass", "less",
    },
    "frontend": {
        "react", "angular", "vue", "svelte", "next.js", "nuxt", "gatsby",
        "remix", "redux", "tailwind", "bootstrap", "material ui", "webpack",
        "vite", "jest", "cypress", "storybook",
    },
    "backend": {
        "django", "flask", "fastapi", "express", "spring", "laravel", "rails",
        "asp.net", "node.js", "deno", "graphql", "rest", "grpc",
    },
    "database": {
        "postgresql", "mysql", "mongodb", "redis", "sqlite", "elasticsearch",
        "dynamodb", "cassandra", "neo4j", "mariadb", "firebase", "supabase",
    },
    "devops": {
        "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
        "jenkins", "github actions", "ci/cd", "nginx", "linux", "helm",
    },
    "ai_ml": {
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "llm",
        "machine learning", "deep learning", "nlp", "computer vision",
        "langchain", "openai", "hugging face", "rag",
    },
    "mobile": {
        "react native", "flutter", "swiftui", "jetpack compose", "kotlin",
        "android", "ios", "expo",
    },
    "tools": {
        "git", "github", "gitlab", "jira", "confluence", "figma", "notion",
        "slack", "vscode", "vim", "postman",
    },
    "soft_skills": {
        "communication", "leadership", "teamwork", "problem solving",
        "critical thinking", "time management", "agile", "scrum",
    },
}


def _infer_category(skill: str) -> str:
    """Infer the category of a skill based on known keyword mappings."""
    s = skill.lower().strip()
    for category, keywords in SKILL_CATEGORIES.items():
        if s in keywords:
            return category
    return "general"


def add_skill_evidence(
    user_id: int,
    skill_name: str,
    source: str,
    evidence: str | None = None,
    source_id: str | None = None,
    project_id: int | None = None,
    certificate_id: int | None = None,
    roadmap_lesson_id: str | None = None,
    related_skills: list[str] | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    """Add evidence for a skill from any source.

    If evidence for this skill+source already exists, update it.
    Returns the current aggregate skill state.
    """
    from app.intelligence.models import SkillEvidence

    existing = SkillEvidence.query.filter_by(
        user_id=user_id,
        skill_name=skill_name.lower().strip(),
        source=source,
    ).first()

    now = datetime.now(timezone.utc)

    if existing:
        if evidence:
            existing.evidence = evidence
        if source_id:
            existing.source_id = source_id
        if project_id:
            existing.project_id = project_id
        if certificate_id:
            existing.certificate_id = certificate_id
        if roadmap_lesson_id:
            existing.roadmap_lesson_id = roadmap_lesson_id
        if related_skills:
            existing.related_skills = list(
                set(existing.related_skills or []) | set(related_skills)
            )
        if confidence is not None:
            existing.confidence = confidence
        existing.updated_at = now
    else:
        category = _infer_category(skill_name)
        existing = SkillEvidence(
            user_id=user_id,
            skill_name=skill_name.lower().strip(),
            category=category,
            source=source,
            evidence=evidence,
            source_id=source_id,
            project_id=project_id,
            certificate_id=certificate_id,
            roadmap_lesson_id=roadmap_lesson_id,
            related_skills=related_skills or [],
            confidence=confidence or _default_confidence(source),
        )
        db.session.add(existing)

    db.session.commit()

    return get_skill_state(user_id, skill_name)


def _default_confidence(source: str) -> float:
    """Return a default confidence level based on evidence source."""
    weights = {
        "assessment": 0.9,
        "certification": 0.85,
        "project": 0.8,
        "roadmap": 0.7,
        "resume": 0.6,
        "linkedin": 0.5,
        "github": 0.5,
        "interview": 0.4,
        "manual": 0.3,
        "course": 0.4,
    }
    return weights.get(source, 0.3)


def get_skill_state(user_id: int, skill_name: str) -> dict[str, Any]:
    """Get the aggregate state of a single skill across all sources."""
    from app.intelligence.models import SkillEvidence

    evidences = SkillEvidence.query.filter_by(
        user_id=user_id,
        skill_name=skill_name.lower().strip(),
    ).all()

    if not evidences:
        return {"skill": skill_name, "confidence": 0.0, "sources": [], "category": None}

    # Aggregate confidence: highest confidence source dominates
    max_confidence = max(e.confidence for e in evidences)
    # Average confidence as secondary metric
    avg_confidence = sum(e.confidence for e in evidences) / len(evidences)

    category = evidences[0].category
    sources = [
        {
            "source": e.source,
            "confidence": e.confidence,
            "evidence": e.evidence,
            "project_id": e.project_id,
            "certificate_id": e.certificate_id,
            "roadmap_lesson_id": e.roadmap_lesson_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in evidences
    ]

    return {
        "skill": skill_name,
        "category": category,
        "confidence": round(max_confidence * 100),
        "confidence_avg": round(avg_confidence * 100),
        "sources_count": len(evidences),
        "sources": sources,
    }


def get_skill_graph(user_id: int) -> dict[str, Any]:
    """Get the complete skill graph for a user."""
    from app.intelligence.models import SkillEvidence

    evidences = (
        SkillEvidence.query.filter_by(user_id=user_id)
        .order_by(SkillEvidence.confidence.desc())
        .all()
    )

    # Deduplicate by skill name, keep highest confidence
    skills: dict[str, dict] = {}
    for e in evidences:
        key = e.skill_name
        if key not in skills or e.confidence > skills[key]["_max_conf"]:
            skills[key] = {
                "skill": e.skill_name,
                "category": e.category or _infer_category(e.skill_name),
                "confidence": round(max(
                    skills.get(key, {}).get("confidence", 0),
                    e.confidence * 100,
                )),
                "sources_count": skills.get(key, {}).get("sources_count", 0) + 1,
                "_max_conf": e.confidence,
            }
        else:
            skills[key]["sources_count"] += 1

    result = sorted(skills.values(), key=lambda x: x["confidence"], reverse=True)

    # Group by category
    by_category: dict[str, list] = {}
    for s in result:
        by_category.setdefault(s["category"], []).append(s)

    return {
        "skills": result,
        "total": len(result),
        "by_category": by_category,
    }


def get_confidence_for_skills(user_id: int, skill_names: list[str]) -> dict[str, int]:
    """Get the aggregate confidence scores for a list of skills."""

    result = {}
    for name in skill_names:
        state = get_skill_state(user_id, name)
        result[name] = state["confidence"]
    return result


def get_top_skills(user_id: int, limit: int = 10) -> list[dict]:
    """Get the top N skills by confidence."""
    graph = get_skill_graph(user_id)
    return graph["skills"][:limit]


def get_weakest_skills(user_id: int, limit: int = 5) -> list[dict]:
    """Get the weakest known skills (useful for recommendations)."""
    graph = get_skill_graph(user_id)
    weakest = [s for s in graph["skills"] if s["confidence"] < 50]
    return weakest[:limit]


def get_missing_skills_for_role(
    user_id: int, target_role: str
) -> list[dict]:
    """Compare user's skills against a role's required skills."""
    from app.career.services.skill_maps import ROLE_SKILL_MAPS

    role_key = target_role.lower().replace(" ", "_")
    required = ROLE_SKILL_MAPS.get(role_key)
    if not required:
        return []

    user_skills = get_skill_graph(user_id)
    known = {s["skill"]: s["confidence"] for s in user_skills["skills"]}

    missing = []
    for skill_req in required:
        skill_name = skill_req["skill"].lower()
        confidence = known.get(skill_name, 0)
        if confidence < 60:
            missing.append({
                "skill": skill_req["skill"],
                "category": skill_req.get("category", "general"),
                "current_confidence": confidence,
                "required_level": skill_req.get("level", "intermediate"),
                "priority": skill_req.get("priority", 5),
                "reason": skill_req.get("reason", ""),
                "learning_time": skill_req.get("learning_time", ""),
                "resources": skill_req.get("resources", []),
            })

    return sorted(missing, key=lambda x: x["priority"], reverse=True)
