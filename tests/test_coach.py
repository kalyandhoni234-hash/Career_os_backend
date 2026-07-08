import pytest
from unittest.mock import patch
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
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
    client.post("/api/auth/signup", json={"email": "coachuser@example.com", "password": "securepass123"})
    client.post("/api/auth/login", json={"email": "coachuser@example.com", "password": "securepass123"})
    return client

def test_chat_requires_login(client):
    response = client.post("/api/coach/chat", json={"message": "hello"})
    assert response.status_code in (401, 302)

def test_chat_requires_message(logged_in_client):
    response = logged_in_client.post("/api/coach/chat", json={})
    assert response.status_code == 400

@patch("app.ai_service.generate_text")
def test_chat_success(mock_generate, logged_in_client):
    mock_generate.return_value = "Here is some career advice."
    response = logged_in_client.post("/api/coach/chat", json={"message": "How do I get a SOC job?"})
    assert response.status_code == 200
    assert response.get_json()["response"] == "Here is some career advice."

@patch("app.ai_service.generate_text")
def test_history_after_chat(mock_generate, logged_in_client):
    mock_generate.return_value = "Advice here."
    logged_in_client.post("/api/coach/chat", json={"message": "hello"})
    response = logged_in_client.get("/api/coach/history")
    messages = response.get_json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

def test_clear_history(logged_in_client):
    response = logged_in_client.delete("/api/coach/history")
    assert response.status_code == 200
