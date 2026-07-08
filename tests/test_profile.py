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
    client.post("/api/auth/signup", json={"email": "profileuser@example.com", "password": "securepass123"})
    client.post("/api/auth/login", json={"email": "profileuser@example.com", "password": "securepass123"})
    return client

def test_get_profile_empty(logged_in_client):
    response = logged_in_client.get("/api/users/profile")
    assert response.status_code == 200
    assert response.get_json()["profile"] is None

def test_create_profile(logged_in_client):
    response = logged_in_client.post("/api/users/profile", json={
        "education": "B.Tech",
        "degree": "Computer Science",
        "graduation_year": 2025,
        "skills": ["Flask", "React"]
    })
    assert response.status_code == 200

def test_get_profile_after_create(logged_in_client):
    logged_in_client.post("/api/users/profile", json={"education": "B.Tech"})
    response = logged_in_client.get("/api/users/profile")
    assert response.status_code == 200
    assert response.get_json()["profile"]["education"] == "B.Tech"

def test_update_profile(logged_in_client):
    logged_in_client.post("/api/users/profile", json={"education": "B.Tech"})
    logged_in_client.post("/api/users/profile", json={"education": "M.Tech"})
    response = logged_in_client.get("/api/users/profile")
    assert response.get_json()["profile"]["education"] == "M.Tech"

def test_profile_requires_login(client):
    response = client.get("/api/users/profile")
    assert response.status_code in (401, 302)
