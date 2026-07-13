import secrets
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, bcrypt, oauth, limiter
from app.core.session import safe_commit
from app import csrf
from app.auth.models import User
from app.email_service import send_reset_email
from app.validation import validate_email_format

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/ping")
def ping():
    return {"blueprint": "auth", "status": "alive"}


@auth_bp.route("/csrf-token", methods=["GET"])
@csrf.exempt
def csrf_token():
    from app.csrf import _generate_token
    token = _generate_token()
    return jsonify({"csrf_token": token}), 200


@auth_bp.route("/signup", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def signup():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if not validate_email_format(email):
        return jsonify({"error": "Invalid email format"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered"}), 409

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(email=email, password_hash=password_hash)
    db.session.add(user)
    safe_commit()

    return jsonify({"message": "Signup successful", "user_id": user.id}), 201


@auth_bp.route("/login", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash:
        return jsonify({"error": "Invalid email or password"}), 401

    if not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    session.permanent = True
    login_user(user, remember=True)
    return jsonify({"message": "Login successful", "user_id": user.id}), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user_id": current_user.id, "email": current_user.email}), 200


@auth_bp.route("/google/login")
def google_login():
    redirect_uri = current_app.config["GOOGLE_REDIRECT_URI"]
    session.permanent = True
    logger.info(
        "OAuth login initiated — redirect_uri=%s, frontend_url=%s, backend_url=%s, is_production=%s",
        redirect_uri,
        current_app.config.get("FRONTEND_URL"),
        current_app.config.get("BACKEND_URL"),
        current_app.config.get("IS_PRODUCTION"),
    )
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    state_from_req = request.args.get("state", "none")
    session_keys = list(session.keys())
    stored_state = session.get("_google_authlib_state_", "NOT_IN_SESSION")
    logger.info(
        "OAuth callback — state_param=%s, session_keys=%s, stored_state=%s, redirect_uri=%s, host=%s",
        state_from_req,
        session_keys,
        str(stored_state)[:20],
        current_app.config.get("GOOGLE_REDIRECT_URI"),
        request.host,
    )

    try:
        token = oauth.google.authorize_access_token()
    except Exception as exc:
        logger.error(
            "OAuth token exchange failed: %s (state_param=%s, stored=%s, session_keys=%s)",
            exc,
            state_from_req,
            str(stored_state)[:20],
            session_keys,
        )
        return redirect(
            current_app.config["FRONTEND_URL"] + "/login?error=oauth_failed"
        )

    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        logger.error("OAuth callback — no userinfo in token")
        return redirect(
            current_app.config["FRONTEND_URL"] + "/login?error=oauth_failed"
        )

    email = user_info["email"].lower()
    user = User.query.filter_by(email=email).first()

    if not user:
        user = User(email=email, oauth_provider="google")
        db.session.add(user)
        safe_commit()

    session.permanent = True
    login_user(user, remember=True)
    logger.info("OAuth login success — email=%s", email)
    return redirect(current_app.config["FRONTEND_URL"] + "/onboarding")


@auth_bp.route("/forgot-password", methods=["POST"])
@csrf.exempt
@limiter.limit("3 per minute")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify(
            {"message": "If that email exists, a reset link has been sent"}
        ), 200

    if not validate_email_format(email):
        return jsonify(
            {"message": "If that email exists, a reset link has been sent"}
        ), 200

    user = User.query.filter_by(email=email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        safe_commit()
        send_reset_email(email, token)

    return jsonify({"message": "If that email exists, a reset link has been sent"}), 200


@auth_bp.route("/reset-password", methods=["POST"])
@csrf.exempt
@limiter.limit("5 per minute")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "")
    new_password = data.get("new_password", "")

    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    user = User.query.filter_by(reset_token=token).first()
    if (
        not user
        or not user.reset_token_expiry
        or user.reset_token_expiry < datetime.utcnow()
    ):
        return jsonify({"error": "Invalid or expired reset token"}), 400

    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    user.reset_token = None
    user.reset_token_expiry = None
    safe_commit()

    return jsonify({"message": "Password reset successful"}), 200


@auth_bp.route("/change-password", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "Current and new password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    if current_user.password_hash:
        if not bcrypt.check_password_hash(current_user.password_hash, current_password):
            return jsonify({"error": "Current password is incorrect"}), 403
    else:
        return jsonify({"error": "Cannot change password on OAuth-only accounts"}), 400

    current_user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    safe_commit()

    return jsonify({"message": "Password changed successfully"}), 200


@auth_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    try:
        db.session.delete(current_user)
        safe_commit()
        logout_user()
        return jsonify({"message": "Account deleted successfully"}), 200
    except Exception as exc:
        logger.error("Failed to delete account for user %s: %s", current_user.id, exc)
        return jsonify({"error": "Failed to delete account"}), 500


@auth_bp.route("/ai-test", methods=["GET"])
@login_required
def ai_test():
    if not current_app.config.get("DEBUG", False):
        return jsonify({"error": "Not available"}), 404
    from app.ai_service import generate_text

    result = generate_text("Say hello in one short sentence.", model="gemini")
    return jsonify({"response": result})
