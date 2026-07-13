from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.core.session import safe_commit
from app.coach.models import CoachMessage

coach_bp = Blueprint("coach", __name__)


@coach_bp.route("/ping")
def ping():
    return {"blueprint": "coach", "status": "alive"}


@coach_bp.route("/history", methods=["GET"])
@login_required
def get_history():
    messages = (
        CoachMessage.query.filter_by(user_id=current_user.id)
        .order_by(CoachMessage.created_at.asc())
        .all()
    )
    return jsonify(
        {
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in messages
            ]
        }
    ), 200


@coach_bp.route("/chat", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def chat():
    from app.ai_service import generate_text

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    if len(user_message) > 2000:
        return jsonify({"error": "Message too long (max 2000 characters)"}), 400

    from app.career.services.career_memory_service import build_career_memory

    memory = build_career_memory(current_user.id)

    memory_str = f"""
Profile: {memory.get('profile', {})}
Career Goal: {memory.get('career_profile', {})}
Resume: {memory.get('resume', {})}
ATS Scores: {memory.get('ats', {})}
Applications: {memory.get('applications', {})}
Skills: {memory.get('skills', {})}
Learning: {memory.get('learning', [])}
Goals: {memory.get('goals', {})}
Roadmaps: {memory.get('roadmaps', [])}
Timeline: {memory.get('timeline', [])}
Score History: {memory.get('score_history', [])}
Recommendations: {memory.get('recommendations', [])}
"""

    history = (
        CoachMessage.query.filter_by(user_id=current_user.id)
        .order_by(CoachMessage.created_at.asc())
        .limit(20)
        .all()
    )
    history_text = ""
    for m in history:
        prefix = "User" if m.role == "user" else "Coach"
        history_text += f"{prefix}: {m.content}\n"

    system_instruction = f"""You are a friendly, direct career coach helping a student/early-career job seeker.
Use the complete Career OS memory context to give specific, actionable advice - not generic platitudes.
Keep responses concise (3-6 sentences unless they ask for a detailed roadmap).

Career Memory Context (includes profile, resume, ATS scores, applications, skills, goals, roadmaps, timeline, recommendations):
{memory_str}

Conversation so far:
{history_text}
"""

    ai_response = generate_text(
        user_message, model="gemini", system_instruction=system_instruction
    )

    user_msg = CoachMessage(user_id=current_user.id, role="user", content=user_message)
    assistant_msg = CoachMessage(
        user_id=current_user.id, role="assistant", content=ai_response
    )
    db.session.add(user_msg)
    db.session.add(assistant_msg)
    safe_commit()

    return jsonify({"response": ai_response}), 200


@coach_bp.route("/history", methods=["DELETE"])
@login_required
def clear_history():
    CoachMessage.query.filter_by(user_id=current_user.id).delete()
    safe_commit()
    return jsonify({"message": "History cleared"}), 200
