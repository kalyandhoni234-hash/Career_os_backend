import secrets
from flask import session, request, jsonify, current_app
from itsdangerous import URLSafeTimedSerializer, BadData

_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/signup", "/api/auth/google"}


def _get_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt="csrf-token"
    )


def _generate_token():
    """Generate a CSRF token, store in session, return the token string."""
    s = _get_serializer()
    token = s.dumps(secrets.token_hex(16))
    session["_csrf_token"] = token
    return token


def _validate_token(token):
    """Returns True if the token is valid and not expired."""
    s = _get_serializer()
    try:
        s.loads(token, max_age=3600)
        return True
    except BadData:
        return False


def exempt(f):
    """Decorator to exempt a view function from CSRF protection."""
    f._csrf_exempt = True
    return f


def protect():
    """Before-request handler: validate CSRF token for state-changing methods.

    Uses the Double Submit Cookie pattern:
      - A CSRF token is always set as a non-httponly cookie.
      - The client must send it back as an ``X-CSRFToken`` header.
      - The server validates that the header token matches the signed cookie value.
    """
    if current_app.config.get("WTF_CSRF_ENABLED", True) is False:
        return
    # Ensure a token exists for any method (including GET) so the
    # cookie is always available for the client to read.
    if "_csrf_token" not in session:
        _generate_token()
    # Only validate for state-changing methods
    if request.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return
    # Exempt login / signup endpoints (they set the initial token)
    if request.path in _EXEMPT_PATHS:
        return
    # Exempt views explicitly decorated with @csrf.exempt
    view_func = current_app.view_functions.get(request.endpoint)
    if view_func and getattr(view_func, "_csrf_exempt", False):
        return
    # Double Submit Cookie: compare cookie value → header value
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRFToken") or request.headers.get(
        "X-CSRF-Token"
    )
    if not cookie_token or not header_token:
        return jsonify({
            "error": "CSRF token missing",
            "code": "INVALID_CSRF_TOKEN",
            "message": "CSRF token cookie or header not found.",
            "details": {},
        }), 403
    if not _validate_token(header_token):
        return jsonify({
            "error": "CSRF token invalid or expired",
            "code": "INVALID_CSRF_TOKEN",
            "message": "CSRF validation failed. Try refreshing the page.",
            "details": {},
        }), 403
    if cookie_token != header_token:
        return jsonify({
            "error": "CSRF token mismatch",
            "code": "INVALID_CSRF_TOKEN",
            "message": "CSRF token in cookie does not match header.",
            "details": {},
        }), 403


def set_csrf_cookie(response):
    """After-request handler: set the CSRF cookie from the session token."""
    token = session.get("_csrf_token")
    if token:
        response.set_cookie(
            "csrf_token",
            token,
            httponly=False,
            samesite="Lax",
            secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        )
    return response
