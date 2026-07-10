import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _strip_trailing_slash(val: str) -> str:
    """Remove trailing slash from a URL string, if present."""
    while val.endswith("/"):
        val = val[:-1]
    return val


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is required. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///career_os.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

    IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"
    SESSION_COOKIE_NAME = "career_os_session"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_NAME = "career_os_remember"
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_HTTPONLY = True

    FRONTEND_URL = _strip_trailing_slash(
        os.environ.get("FRONTEND_URL", "http://localhost:3000")
    )
    BACKEND_URL = _strip_trailing_slash(
        os.environ.get("BACKEND_URL", "http://127.0.0.1:5000")
    )

    # Explicit redirect URI for Google OAuth.  When set, takes precedence over
    # the auto-derived value.  This MUST be an exact match for one of the
    # "Authorized redirect URIs" in the Google Cloud Console.
    _explicit_google_redirect = os.environ.get("GOOGLE_REDIRECT_URI")
    if _explicit_google_redirect:
        GOOGLE_REDIRECT_URI = _strip_trailing_slash(_explicit_google_redirect)
    else:
        GOOGLE_REDIRECT_URI = _strip_trailing_slash(
            FRONTEND_URL + "/api/auth/google/callback"
        )
