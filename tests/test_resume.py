import pytest
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        "WTF_CSRF_ENABLED": False,
    })
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
    client.post("/api/auth/signup", json={"email": "resumeuser@example.com", "password": "securepass123"})
    client.post("/api/auth/login", json={"email": "resumeuser@example.com", "password": "securepass123"})
    return client

def test_get_resume_empty(logged_in_client):
    response = logged_in_client.get("/api/resume")
    assert response.status_code == 200
    assert response.get_json()["resume"] is None

def test_create_resume(logged_in_client):
    response = logged_in_client.post("/api/resume", json={
        "full_name": "Test User",
        "summary": "A short summary",
        "skills": ["Python", "Flask"]
    })
    assert response.status_code == 200

def test_get_resume_after_create(logged_in_client):
    logged_in_client.post("/api/resume", json={"full_name": "Test User"})
    response = logged_in_client.get("/api/resume")
    assert response.get_json()["resume"]["full_name"] == "Test User"

def test_update_resume(logged_in_client):
    logged_in_client.post("/api/resume", json={"full_name": "First Name"})
    logged_in_client.post("/api/resume", json={"full_name": "Updated Name"})
    response = logged_in_client.get("/api/resume")
    assert response.get_json()["resume"]["full_name"] == "Updated Name"

def test_resume_requires_login(client):
    response = client.get("/api/resume")
    assert response.status_code in (401, 302)
