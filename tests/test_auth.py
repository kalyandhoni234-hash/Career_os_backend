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

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"

def test_signup_success(client):
    response = client.post("/api/auth/signup", json={
        "email": "newuser@example.com",
        "password": "securepass123"
    })
    assert response.status_code == 201
    assert "user_id" in response.get_json()

def test_signup_missing_fields(client):
    response = client.post("/api/auth/signup", json={"email": "onlyemail@example.com"})
    assert response.status_code == 400

def test_signup_duplicate_email(client):
    client.post("/api/auth/signup", json={"email": "dupe@example.com", "password": "securepass123"})
    response = client.post("/api/auth/signup", json={"email": "dupe@example.com", "password": "anotherpass123"})
    assert response.status_code == 409

def test_login_success(client):
    client.post("/api/auth/signup", json={"email": "loginuser@example.com", "password": "securepass123"})
    response = client.post("/api/auth/login", json={"email": "loginuser@example.com", "password": "securepass123"})
    assert response.status_code == 200

def test_login_wrong_password(client):
    client.post("/api/auth/signup", json={"email": "wrongpass@example.com", "password": "securepass123"})
    response = client.post("/api/auth/login", json={"email": "wrongpass@example.com", "password": "badpassword"})
    assert response.status_code == 401

def test_login_nonexistent_user(client):
    response = client.post("/api/auth/login", json={"email": "nouser@example.com", "password": "whatever123"})
    assert response.status_code == 401
