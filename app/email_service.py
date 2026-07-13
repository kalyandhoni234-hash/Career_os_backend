import logging
from flask import current_app

logger = logging.getLogger(__name__)


def send_reset_email(to_email, token):
    reset_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={token}"
    subject = "Career OS - Password Reset"
    body = f"Click the link to reset your password: {reset_url}"

    if current_app.config.get("IS_PRODUCTION"):
        logger.info(
            "PRODUCTION MODE: Would send password reset email to %s with URL: %s",
            to_email,
            reset_url,
        )
    else:
        logger.info(
            "DEV MODE: Password reset email for %s\nTo: %s\nSubject: %s\nBody: %s",
            to_email,
            to_email,
            subject,
            body,
        )
