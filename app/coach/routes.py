from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.coach.models import CoachMessage
from app.users.models import Profile
from app.resume.models import Resume

coach_bp = Blueprint("coach", __name__)

@coach_bp.route("/ping")
def ping():
    return {"blueprint": "coach", "status": "alive"}

@coach_bp.route("/history", methods=["GET"])
@login_required
def get_history():
    messages = CoachMessage.query.filter_by(user_id=current_user.id).order_by(CoachMessage.created_at.asc()).all()
    return jsonify({
        "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]
    }), 200

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

    profile = Profile.query.filter_by(user_id=current_user.id).first()
    resume = Resume.query.filter_by(user_id=current_user.id).first()

    profile_context = "No profile set yet."
    if profile:
        profile_context = f"""
Education: {profile.education or "not set"}
Degree: {profile.degree or "not set"}
Target roles: {profile.preferred_roles or "not set"}
Skills: {profile.skills or "not set"}
"""

    resume_context = "No resume created yet."
    if resume:
        resume_context = f"""
Summary: {resume.summary or "not set"}
Skills: {", ".join(resume.skills or [])}
"""

    history = CoachMessage.query.filter_by(user_id=current_user.id).order_by(CoachMessage.created_at.asc()).limit(20).all()
    history_text = ""
    for m in history:
        prefix = "User" if m.role == "user" else "Coach"
        history_text += f"{prefix}: {m.content}\n"

    system_instruction = f"""You are a friendly, direct career coach helping a student/early-career job seeker.
Use their profile and resume context to give specific, actionable advice - not generic platitudes.
Keep responses concise (3-6 sentences unless they ask for a detailed roadmap).

User Profile:
{profile_context}

User Resume:
{resume_context}

Conversation so far:
{history_text}
"""

    ai_response = generate_text(user_message, model="gemini", system_instruction=system_instruction)

    user_msg = CoachMessage(user_id=current_user.id, role="user", content=user_message)
    assistant_msg = CoachMessage(user_id=current_user.id, role="assistant", content=ai_response)
    db.session.add(user_msg)
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({"response": ai_response}), 200

@coach_bp.route("/history", methods=["DELETE"])
@login_required
def clear_history():
    CoachMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"message": "History cleared"}), 200
