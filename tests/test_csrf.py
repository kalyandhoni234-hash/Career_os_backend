import pytest
import time
from unittest import mock
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            "WTF_CSRF_ENABLED": True,
            "DEBUG": False,
            "SECRET_KEY": "fixed-test-secret-for-csrf-tests",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "securepass123"},
    )
    client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "securepass123"},
    )
    return client


def test_exempt_endpoints_work_without_token(client):
    """Auth entry points (exempt) should work without any CSRF token."""
    r = client.post(
        "/api/auth/signup",
        json={"email": "exempt@example.com", "password": "securepass123"},
    )
    assert r.status_code == 201

    r = client.post(
        "/api/auth/login",
        json={"email": "exempt@example.com", "password": "securepass123"},
    )
    assert r.status_code == 200


def test_protected_endpoint_rejects_missing_token(logged_in_client):
    """Protected POST without CSRF token should return 403."""
    r = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
    )
    assert r.status_code == 403
    data = r.get_json()
    assert data["error"] == "CSRF token missing"
    assert data["code"] == "INVALID_CSRF_TOKEN"


def test_protected_endpoint_rejects_empty_header(logged_in_client):
    """Protected POST with empty X-CSRFToken header should return 403."""
    r = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
        headers={"X-CSRFToken": ""},
    )
    assert r.status_code == 403


def test_protected_endpoint_succeeds_with_valid_token(logged_in_client):
    """Protected POST with valid CSRF token should succeed."""
    token_resp = logged_in_client.get("/api/auth/csrf-token")
    token = token_resp.get_json()["csrf_token"]

    r = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
        headers={"X-CSRFToken": token},
    )
    assert r.status_code == 200


def test_protected_endpoint_rejects_tampered_token(logged_in_client):
    """Protected POST with tampered token should return 403."""
    token_resp = logged_in_client.get("/api/auth/csrf-token")
    token = token_resp.get_json()["csrf_token"]

    tampered = token[:-5] + "XXXXX"
    r = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
        headers={"X-CSRFToken": tampered},
    )
    assert r.status_code == 403


def test_protected_endpoint_rejects_garbage_token(logged_in_client):
    """Protected POST with random garbage token should return 403."""
    r = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
        headers={"X-CSRFToken": "this-is-completely-random-garbage"},
    )
    assert r.status_code == 403


def test_protected_endpoint_rejects_token_from_different_secret(logged_in_client, app):
    """A token signed with a different secret should be rejected."""
    wrong_signer = URLSafeTimedSerializer("different-secret", salt="csrf-token")
    forged_token = wrong_signer.dumps("csrf")

    r = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
        headers={"X-CSRFToken": forged_token},
    )
    assert r.status_code == 403


def test_expired_token_is_rejected(logged_in_client, app):
    """An expired CSRF token should return 403."""
    from app.csrf import _generate_token, _validate_token

    with app.test_request_context():
        token = _generate_token()
        assert _validate_token(token) is True

        with mock.patch("time.time", return_value=time.time() + 7200):
            assert _validate_token(token) is False


def test_x_csrf_token_header_alternative_name_works(logged_in_client):
    """X-CSRF-Token (with hyphen) should also work."""
    token_resp = logged_in_client.get("/api/auth/csrf-token")
    token = token_resp.get_json()["csrf_token"]

    r = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200


def test_get_endpoints_are_not_affected(logged_in_client):
    """GET requests should never require CSRF tokens."""
    r = logged_in_client.get("/api/auth/me")
    assert r.status_code == 200


def test_logout_requires_csrf(logged_in_client):
    """Logout (POST) is a protected endpoint and requires CSRF."""
    r = logged_in_client.post("/api/auth/logout")
    assert r.status_code == 403

    token_resp = logged_in_client.get("/api/auth/csrf-token")
    token = token_resp.get_json()["csrf_token"]
    r = logged_in_client.post(
        "/api/auth/logout",
        headers={"X-CSRFToken": token},
    )
    assert r.status_code == 200


def test_delete_account_requires_csrf(logged_in_client):
    """Delete account (POST) is a protected endpoint and requires CSRF."""
    r = logged_in_client.post("/api/auth/delete-account")
    assert r.status_code == 403

    token_resp = logged_in_client.get("/api/auth/csrf-token")
    token = token_resp.get_json()["csrf_token"]
    r = logged_in_client.post(
        "/api/auth/delete-account",
        headers={"X-CSRFToken": token},
    )
    assert r.status_code == 200


def test_csrf_cookie_is_set_on_response(client):
    """The csrf_token cookie should be set after fetching a token."""
    r = client.get("/api/auth/csrf-token")
    assert "csrf_token" in r.headers.get("Set-Cookie", "")


def test_csrf_token_is_url_safe(client):
    """CSRF token should be URL-safe (no + or / characters)."""
    r = client.get("/api/auth/csrf-token")
    token = r.get_json()["csrf_token"]
    # itsdangerous URLSafeTimedSerializer uses URL-safe base64
    assert "+" not in token
    assert "/" not in token


def test_csrf_cookie_is_not_httponly(client):
    """CSRF cookie must be readable by JavaScript."""
    r = client.get("/api/auth/csrf-token")
    cookie_header = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" not in cookie_header


def test_multiple_tokens_are_all_valid(logged_in_client):
    """Each call to csrf-token generates a unique token; only the latest is valid."""
    token1 = logged_in_client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    token2 = logged_in_client.get("/api/auth/csrf-token").get_json()["csrf_token"]
    token3 = logged_in_client.get("/api/auth/csrf-token").get_json()["csrf_token"]

    assert token1 != token2
    assert token2 != token3

    # Only the latest token is valid (cookie was updated each time)
    r = logged_in_client.post(
        "/api/auth/logout",
        headers={"X-CSRFToken": token3},
    )
    assert r.status_code == 200
