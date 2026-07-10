import pytest
from unittest.mock import patch
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
        json={"email": "reviewuser@example.com", "password": "securepass123"},
    )
    client.post(
        "/api/auth/login",
        json={"email": "reviewuser@example.com", "password": "securepass123"},
    )
    return client


def test_review_requires_resume(logged_in_client):
    response = logged_in_client.post("/api/resume/review")
    assert response.status_code == 404


@patch("app.ai_service.generate_text")
def test_review_success(mock_generate, logged_in_client):
    mock_generate.return_value = """{
        "ats_score": 75,
        "strengths": ["Good summary"],
        "weaknesses": ["Missing metrics"],
        "missing_keywords": ["Python"],
        "weak_action_verbs": ["did"],
        "suggestions": ["Add numbers to bullet points"]
    }"""
    logged_in_client.post(
        "/api/resume", json={"full_name": "Test User", "summary": "A summary"}
    )
    response = logged_in_client.post("/api/resume/review")
    assert response.status_code == 200
    review = response.get_json()["review"]
    assert review["ats_score"] == 75


@patch("app.ai_service.generate_text")
def test_review_handles_bad_json(mock_generate, logged_in_client):
    mock_generate.return_value = "not valid json at all"
    logged_in_client.post("/api/resume", json={"full_name": "Test User"})
    response = logged_in_client.post("/api/resume/review")
    assert response.status_code == 500
