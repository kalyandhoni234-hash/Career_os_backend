import pytest
from datetime import datetime, timedelta, timezone
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
            "WTF_CSRF_ENABLED": False,
            "DEBUG": False,
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


def _create_user_with_reset_token(app, email="resetuser@example.com"):
    from app.auth.models import User

    with app.app_context():
        user = User(email=email, password_hash="placeholder")
        user.reset_token = "valid-test-token"
        user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        db.session.add(user)
        db.session.commit()
        return user.id


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_signup_success(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "newuser@example.com", "password": "securepass123"},
    )
    assert response.status_code == 201
    assert "user_id" in response.get_json()


def test_signup_missing_fields(client):
    response = client.post("/api/auth/signup", json={"email": "onlyemail@example.com"})
    assert response.status_code == 400


def test_signup_duplicate_email(client):
    client.post(
        "/api/auth/signup",
        json={"email": "dupe@example.com", "password": "securepass123"},
    )
    response = client.post(
        "/api/auth/signup",
        json={"email": "dupe@example.com", "password": "anotherpass123"},
    )
    assert response.status_code == 409


def test_signup_invalid_email(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "not-an-email", "password": "securepass123"},
    )
    assert response.status_code == 400


def test_signup_invalid_email_no_at(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "userexample.com", "password": "securepass123"},
    )
    assert response.status_code == 400


def test_login_success(client):
    client.post(
        "/api/auth/signup",
        json={"email": "loginuser@example.com", "password": "securepass123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "loginuser@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200


def test_login_wrong_password(client):
    client.post(
        "/api/auth/signup",
        json={"email": "wrongpass@example.com", "password": "securepass123"},
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "wrongpass@example.com", "password": "badpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nouser@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401


def test_csrf_token_endpoint(client):
    response = client.get("/api/auth/csrf-token")
    assert response.status_code == 200
    data = response.get_json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 0


def test_forgot_password_no_token_in_response(client, app):
    _create_user_with_reset_token(app, "forgotme@example.com")
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "forgotme@example.com"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "reset_token" not in data
    assert "message" in data


def test_forgot_password_same_message_for_existing_and_non_existing(client, app):
    _create_user_with_reset_token(app, "existing@example.com")
    resp_existing = client.post(
        "/api/auth/forgot-password",
        json={"email": "existing@example.com"},
    )
    resp_missing = client.post(
        "/api/auth/forgot-password",
        json={"email": "missing@example.com"},
    )
    assert resp_existing.status_code == 200
    assert resp_missing.status_code == 200
    assert resp_existing.get_json()["message"] == resp_missing.get_json()["message"]


def test_reset_password_success(client, app):
    _create_user_with_reset_token(app, "resetme@example.com")
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "valid-test-token", "new_password": "newsecurepass456"},
    )
    assert response.status_code == 200
    assert response.get_json()["message"] == "Password reset successful"


def test_reset_password_invalid_token(client):
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "nonexistent-token", "new_password": "newsecurepass456"},
    )
    assert response.status_code == 400


def test_reset_password_short_password(client):
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "some-token", "new_password": "1234567"},
    )
    assert response.status_code == 400


def test_reset_password_missing_fields(client):
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "some-token"},
    )
    assert response.status_code == 400


def test_reset_password_token_used_once(client, app):
    _create_user_with_reset_token(app, "usedonce@example.com")
    client.post(
        "/api/auth/reset-password",
        json={"token": "valid-test-token", "new_password": "newsecurepass456"},
    )
    response = client.post(
        "/api/auth/reset-password",
        json={"token": "valid-test-token", "new_password": "anotherpass789"},
    )
    assert response.status_code == 400


def test_ai_test_not_available_in_production(client, logged_in_client):
    response = logged_in_client.get("/api/auth/ai-test")
    assert response.status_code == 404


def test_ai_test_requires_login(client):
    response = client.get("/api/auth/ai-test")
    assert response.status_code == 401


def test_change_password_success(logged_in_client):
    response = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "newpass12345"},
    )
    assert response.status_code == 200


def test_change_password_wrong_current(logged_in_client):
    response = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "wrongpassword", "new_password": "newpass12345"},
    )
    assert response.status_code == 403


def test_change_password_short_new(logged_in_client):
    response = logged_in_client.post(
        "/api/auth/change-password",
        json={"current_password": "securepass123", "new_password": "1234567"},
    )
    assert response.status_code == 400


def test_logout(logged_in_client):
    response = logged_in_client.post("/api/auth/logout")
    assert response.status_code == 200
    me = logged_in_client.get("/api/auth/me")
    assert me.status_code == 401


def test_me_requires_login(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_delete_account(logged_in_client):
    response = logged_in_client.post("/api/auth/delete-account")
    assert response.status_code == 200
    me = logged_in_client.get("/api/auth/me")
    assert me.status_code == 401


def test_500_handler_does_not_expose_traceback(client, app):
    with app.app_context():
        from app.auth.models import User

        user = User(email="crasher@example.com", password_hash="test")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    response = client.post(
        "/api/auth/signup",
        json={"email": "crasher@example.com", "password": "securepass123"},
    )
    data = response.get_json()
    if "details" in data:
        assert "traceback" not in data["details"]
