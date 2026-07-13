import json
import logging
import os
from datetime import datetime, timezone

from app.extensions import db
from app.career.models import Roadmap, LessonProgress

logger = logging.getLogger(__name__)

_ROADMAP_DEFS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "roadmaps"
)

_ROADMAP_CACHE: dict[str, dict] | None = None


def _load_all_roadmap_defs() -> dict[str, dict]:
    """Load all roadmap JSON definitions into a dict keyed by role key."""
    global _ROADMAP_CACHE
    if _ROADMAP_CACHE is not None:
        return _ROADMAP_CACHE

    defs = {}
    if not os.path.isdir(_ROADMAP_DEFS_DIR):
        logger.warning("Roadmap definitions directory not found: %s", _ROADMAP_DEFS_DIR)
        _ROADMAP_CACHE = {}
        return _ROADMAP_CACHE

    for fname in os.listdir(_ROADMAP_DEFS_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(_ROADMAP_DEFS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            role_title = data.get("title", "").lower().replace(" ", "_")
            defs[role_title] = data
            # Also index by the raw title
            defs[data.get("title", "").lower()] = data
        except Exception as e:
            logger.error("Failed to load roadmap def %s: %s", fname, e)

    _ROADMAP_CACHE = defs
    logger.info("Loaded %d roadmap definitions", len(defs))
    return defs


def get_available_career_paths() -> list[dict]:
    """Return list of available career paths with metadata."""
    defs = _load_all_roadmap_defs()
    paths = []
    seen = set()
    for data in defs.values():
        title = data.get("title", "")
        if title in seen:
            continue
        seen.add(title)
        total_lessons = sum(
            1 for ph in data.get("phases", [])
            for mod in ph.get("modules", [])
            for _ in mod.get("lessons", [])
        )
        paths.append({
            "title": title,
            "description": data.get("description", ""),
            "estimated_months": data.get("estimated_months", 12),
            "total_lessons": total_lessons,
            "phase_count": len(data.get("phases", [])),
        })
    return paths


def find_roadmap_def(target_role: str | None) -> dict | None:
    """Find the best-matching roadmap definition for a target role."""
    if not target_role:
        return None
    defs = _load_all_roadmap_defs()
    key = target_role.lower().strip()

    if key in defs:
        return defs[key]

    for k, data in defs.items():
        title = data.get("title", "").lower()
        if key in title or title in key:
            return data

    return None


def generate_personalized_roadmap(user_id: int, target_role: str | None = None) -> dict | None:
    """Generate a personalized roadmap for the user based on their profile and existing skills."""
    from app.career.models import CareerProfile, UserSkill
    from app.resume.models import Resume

    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    role = target_role or (cp.target_role if cp else None)
    if not role:
        return None

    defn = find_roadmap_def(role)
    if not defn:
        logger.warning("No roadmap definition found for role: %s", role)
        return None

    # Gather user's existing skills to skip known lessons
    existing_skills = set()
    resume = Resume.query.filter_by(user_id=user_id).first()
    if resume and resume.skills:
        for s in resume.skills:
            if isinstance(s, str):
                existing_skills.add(s.lower().strip())
    for us in UserSkill.query.filter_by(user_id=user_id).all():
        existing_skills.add(us.name.lower().strip())

    # Check for existing active roadmap; if found and same role, return it
    existing_rm = Roadmap.query.filter_by(
        user_id=user_id, target_role=defn["title"], status="active"
    ).first()
    if existing_rm:
        return get_roadmap_with_progress(existing_rm.id)

    # Create new roadmap
    roadmap = Roadmap(
        user_id=user_id,
        title=f"{defn['title']} Learning Roadmap",
        description=defn.get("description", ""),
        target_role=defn["title"],
        category=defn["title"].lower().replace(" ", "_"),
        estimated_weeks=defn.get("estimated_months", 12) * 4,
        status="active",
        source="ai_generated",
        definition=defn,
        current_phase_id=None,
        current_module_id=None,
        current_lesson_id=None,
    )
    db.session.add(roadmap)
    db.session.flush()

    # Create LessonProgress entries, skipping lessons for known skills
    first_lesson_id = None
    for phase in defn.get("phases", []):
        for module in phase.get("modules", []):
            for lesson in module.get("lessons", []):
                skills = [s.lower() for s in lesson.get("skills_gained", [])]
                has_skills = any(s in existing_skills for s in skills)
                status = "completed" if has_skills else "not_started"

                lp = LessonProgress(
                    roadmap_id=roadmap.id,
                    user_id=user_id,
                    lesson_id=lesson["id"],
                    phase_id=phase["id"],
                    module_id=module["id"],
                    status=status,
                    completed_at=datetime.now(timezone.utc) if has_skills else None,
                )
                db.session.add(lp)

                if first_lesson_id is None and status == "not_started":
                    first_lesson_id = lesson["id"]
                    roadmap.current_lesson_id = lesson["id"]
                    roadmap.current_module_id = module["id"]
                    roadmap.current_phase_id = phase["id"]

    if first_lesson_id is None:
        roadmap.status = "completed"
        roadmap.progress = 100

    db.session.commit()

    # Log timeline event
    from app.career.models import CareerTimelineEvent
    event = CareerTimelineEvent(
        user_id=user_id,
        event_type="roadmap",
        title=f"Personalized Roadmap Started: {defn['title']}",
        description="Auto-generated roadmap with personalized lesson plan based on existing skills",
        event_date=datetime.now(timezone.utc),
        importance=4,
    )
    db.session.add(event)
    db.session.commit()

    return get_roadmap_with_progress(roadmap.id)


def get_roadmap_with_progress(roadmap_id: int) -> dict | None:
    """Get a roadmap with full phase/module/lesson hierarchy merged with progress."""
    roadmap = Roadmap.query.get(roadmap_id)
    if not roadmap:
        return None

    definition = roadmap.definition
    if not definition:
        return None

    # Load all lesson progress for this roadmap
    progress_map: dict[str, dict] = {}
    for lp in LessonProgress.query.filter_by(roadmap_id=roadmap_id).all():
        progress_map[lp.lesson_id] = {
            "status": lp.status,
            "score": lp.score,
            "notes": lp.notes,
            "started_at": lp.started_at.isoformat() if lp.started_at else None,
            "completed_at": lp.completed_at.isoformat() if lp.completed_at else None,
        }

    total = len(progress_map)
    completed = sum(1 for p in progress_map.values() if p["status"] == "completed")

    # Compute progress if not set
    if total > 0:
        roadmap.progress = int((completed / total) * 100)
        db.session.commit()

    # Build enriched phases with progress
    phases = []
    for phase in definition.get("phases", []):
        enriched_modules = []
        for module in phase.get("modules", []):
            enriched_lessons = []
            for lesson in module.get("lessons", []):
                p = progress_map.get(lesson["id"], {"status": "not_started"})
                enriched_lessons.append({
                    **lesson,
                    "status": p["status"],
                    "progress_score": p.get("score"),
                    "progress_notes": p.get("notes"),
                    "started_at": p.get("started_at"),
                    "completed_at": p.get("completed_at"),
                })
            enriched_modules.append({
                "id": module["id"],
                "title": module["title"],
                "order": module["order"],
                "lessons": enriched_lessons,
                "progress": _module_progress(enriched_lessons),
            })
        phases.append({
            "id": phase["id"],
            "title": phase["title"],
            "order": phase["order"],
            "modules": enriched_modules,
            "progress": _phase_progress(enriched_modules),
        })

    # Find current lesson
    current_lesson = None
    current_module_title = None
    current_phase_title = None
    if roadmap.current_lesson_id:
        for ph in phases:
            for mod in ph["modules"]:
                for les in mod["lessons"]:
                    if les["id"] == roadmap.current_lesson_id:
                        current_lesson = les
                        current_module_title = mod["title"]
                        current_phase_title = ph["title"]
                        break

    # Default to first unstarted lesson if none set
    if not current_lesson:
        for ph in phases:
            for mod in ph["modules"]:
                for les in mod["lessons"]:
                    if les.get("status") == "not_started":
                        current_lesson = les
                        current_module_title = mod["title"]
                        current_phase_title = ph["title"]
                        roadmap.current_lesson_id = les["id"]
                        roadmap.current_module_id = mod["id"]
                        roadmap.current_phase_id = ph["id"]
                        db.session.commit()
                        break
                if current_lesson:
                    break
            if current_lesson:
                break

    # Compute totals
    total_lessons_count = total
    completed_count = completed
    not_started_count = sum(1 for p in progress_map.values() if p["status"] == "not_started")
    in_progress_count = sum(1 for p in progress_map.values() if p["status"] == "in_progress")

    result = {
        "id": roadmap.id,
        "title": roadmap.title,
        "description": roadmap.description,
        "target_role": roadmap.target_role,
        "category": roadmap.category,
        "estimated_weeks": roadmap.estimated_weeks,
        "progress": roadmap.progress,
        "status": roadmap.status,
        "streak": roadmap.streak,
        "weekly_hours": roadmap.weekly_hours,
        "created_at": roadmap.created_at.isoformat() if roadmap.created_at else None,
        "started_at": roadmap.started_at.isoformat() if roadmap.started_at else None,
        "last_activity_at": roadmap.last_activity_at.isoformat() if roadmap.last_activity_at else None,
        "phases": phases,
        "current_phase_title": current_phase_title,
        "current_module_title": current_module_title,
        "current_lesson": current_lesson,
        "totals": {
            "total": total_lessons_count,
            "completed": completed_count,
            "in_progress": in_progress_count,
            "not_started": not_started_count,
        },
    }
    return result


def _module_progress(lessons: list) -> int:
    """Calculate module progress percentage."""
    if not lessons:
        return 0
    completed = sum(1 for les in lessons if les.get("status") == "completed")
    return int((completed / len(lessons)) * 100)


def _phase_progress(modules: list) -> int:
    """Calculate phase progress percentage."""
    if not modules:
        return 0
    total = sum(1 for m in modules for _ in m.get("lessons", []))
    completed = sum(
        1 for mod in modules for les in mod.get("lessons", []) if les.get("status") == "completed"
    )
    return int((completed / total) * 100) if total else 0


def update_lesson_progress(
    user_id: int,
    roadmap_id: int,
    lesson_id: str,
    status: str,
    score: int | None = None,
    notes: str | None = None,
) -> dict | None:
    """Update progress for a specific lesson and advance to next lesson."""
    roadmap = Roadmap.query.filter_by(id=roadmap_id, user_id=user_id).first()
    if not roadmap:
        return None

    lp = LessonProgress.query.filter_by(
        roadmap_id=roadmap_id, lesson_id=lesson_id
    ).first()
    if not lp:
        return None

    now = datetime.now(timezone.utc)

    if status == "in_progress" and lp.status == "not_started":
        lp.status = "in_progress"
        lp.started_at = now
        roadmap.last_activity_at = now

    elif status == "completed" and lp.status != "completed":
        lp.status = "completed"
        lp.completed_at = now
        lp.score = score
        lp.notes = notes
        roadmap.last_activity_at = now

        # Update streak
        roadmap.streak = _update_streak(roadmap, now)

        # Advance to next lesson
        _advance_to_next_lesson(roadmap, lesson_id)

    elif status == "skipped":
        lp.status = "skipped"
        roadmap.last_activity_at = now
        _advance_to_next_lesson(roadmap, lesson_id)

    elif status == "need_revision":
        lp.status = "need_revision"
        roadmap.last_activity_at = now

    # Recalculate progress
    all_progress = LessonProgress.query.filter_by(roadmap_id=roadmap_id).all()
    total = len(all_progress)
    completed = sum(1 for p in all_progress if p.status == "completed")
    roadmap.progress = int((completed / total) * 100) if total else 0

    if roadmap.progress == 100:
        roadmap.status = "completed"
        from app.career.models import CareerTimelineEvent
        event = CareerTimelineEvent(
            user_id=user_id,
            event_type="roadmap",
            title=f"Roadmap Completed: {roadmap.title}",
            description=f"Completed all {total} lessons",
            event_date=now,
            importance=5,
        )
        db.session.add(event)

    db.session.commit()
    return get_roadmap_with_progress(roadmap_id)


def _update_streak(roadmap: Roadmap, now: datetime) -> int:
    """Calculate and update streak based on last activity."""
    if not roadmap.last_activity_at:
        return 1
    days_since = (now - roadmap.last_activity_at).days
    if days_since <= 1:
        return (roadmap.streak or 0) + 1
    elif days_since <= 3:
        return roadmap.streak or 1
    else:
        return 1


def _advance_to_next_lesson(roadmap: Roadmap, current_lesson_id: str):
    """Find and set the next uncompleted lesson as current."""
    definition = roadmap.definition
    if not definition:
        return

    # Flatten all lessons into ordered list
    all_lessons = []
    for phase in definition.get("phases", []):
        for module in phase.get("modules", []):
            for lesson in module.get("lessons", []):
                all_lessons.append({
                    "lesson_id": lesson["id"],
                    "phase_id": phase["id"],
                    "module_id": module["id"],
                })

    # Find current position
    current_idx = None
    for i, item in enumerate(all_lessons):
        if item["lesson_id"] == current_lesson_id:
            current_idx = i
            break

    if current_idx is None:
        return

    # Look for next uncompleted lesson
    for item in all_lessons[current_idx + 1:]:
        existing = LessonProgress.query.filter_by(
            roadmap_id=roadmap.id, lesson_id=item["lesson_id"]
        ).first()
        if existing and existing.status in ("not_started", "in_progress", "need_revision"):
            roadmap.current_lesson_id = item["lesson_id"]
            roadmap.current_module_id = item["module_id"]
            roadmap.current_phase_id = item["phase_id"]
            return


def get_dashboard_roadmap(user_id: int) -> dict | None:
    """Get a compact roadmap summary for the dashboard."""
    roadmap = Roadmap.query.filter_by(user_id=user_id, status="active").first()
    if not roadmap:
        return None

    full = get_roadmap_with_progress(roadmap.id)
    if not full:
        return None

    now = datetime.now(timezone.utc)
    started = roadmap.started_at or now
    days_active = (now - started).days or 1
    target_days = (roadmap.estimated_weeks or 12) * 7
    days_remaining = max(0, target_days - days_active)
    completion_rate = roadmap.progress / 100 if roadmap.progress else 0
    est_remaining_days = int(days_remaining * (1 - completion_rate)) if completion_rate < 1 else 0

    return {
        "id": roadmap.id,
        "title": roadmap.title,
        "target_role": roadmap.target_role,
        "progress": roadmap.progress,
        "streak": roadmap.streak,
        "weekly_hours": roadmap.weekly_hours,
        "status": roadmap.status,
        "current_phase_title": full.get("current_phase_title"),
        "current_module_title": full.get("current_module_title"),
        "current_lesson": full.get("current_lesson"),
        "totals": full.get("totals"),
        "days_active": days_active,
        "estimated_days_remaining": est_remaining_days,
        "days_remaining": days_remaining,
        "started_at": roadmap.started_at.isoformat() if roadmap.started_at else None,
        "last_activity_at": roadmap.last_activity_at.isoformat() if roadmap.last_activity_at else None,
    }


def auto_generate_on_onboarding(user_id: int):
    """Auto-generate a roadmap when onboarding is completed."""
    from app.career.models import CareerProfile
    cp = CareerProfile.query.filter_by(user_id=user_id).first()
    if not cp or not cp.target_role:
        logger.info("No target role set for user %s, skipping auto-roadmap", user_id)
        return None

    result = generate_personalized_roadmap(user_id, target_role=cp.target_role)
    if result:
        logger.info("Auto-generated roadmap for user %s role=%s", user_id, cp.target_role)
    return result


def recommend_next_lesson(roadmap_id: int, lesson_id: str) -> dict:
    """Generate AI recommendations after completing a lesson."""
    result: dict = {
        "next_lesson": None,
        "projects": [],
        "resources": [],
    }

    try:
        lp = LessonProgress.query.filter_by(
            roadmap_id=roadmap_id, lesson_id=lesson_id
        ).first()
        if not lp or lp.status != "completed":
            return result

        roadmap = Roadmap.query.get(roadmap_id)
        if not roadmap or not roadmap.definition:
            return result

        completed_lesson = None
        for phase in roadmap.definition.get("phases", []):
            for module in phase.get("modules", []):
                for lesson in module.get("lessons", []):
                    if lesson["id"] == lesson_id:
                        completed_lesson = lesson
                        break

        if not completed_lesson:
            return result

        # Next lesson recommendation
        next_lp = LessonProgress.query.filter_by(
            roadmap_id=roadmap_id, status="not_started"
        ).order_by(LessonProgress.id).first()

        if next_lp:
            for phase in roadmap.definition.get("phases", []):
                for module in phase.get("modules", []):
                    for lesson in module.get("lessons", []):
                        if lesson["id"] == next_lp.lesson_id:
                            result["next_lesson"] = lesson["title"]
                            break

        # Project recommendation
        if completed_lesson.get("projects"):
            result["projects"] = [p["title"] for p in completed_lesson["projects"]]

        # Resource recommendations
        resources = completed_lesson.get("resources", [])
        if resources:
            result["resources"] = [r["title"] for r in resources[:3]]

    except Exception as e:
        logger.error("Recommend next lesson error: %s", e, exc_info=True)

    return result
