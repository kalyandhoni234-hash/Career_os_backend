import pytest
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
        json={"email": "jobsuser@example.com", "password": "securepass123"},
    )
    client.post(
        "/api/auth/login",
        json={"email": "jobsuser@example.com", "password": "securepass123"},
    )
    return client


def test_list_jobs_empty(logged_in_client):
    response = logged_in_client.get("/api/jobs")
    assert response.status_code == 200
    assert response.get_json()["jobs"] == []


def test_create_job(logged_in_client):
    response = logged_in_client.post(
        "/api/jobs", json={"company": "Google", "role": "SOC Analyst"}
    )
    assert response.status_code == 201
    assert response.get_json()["job"]["status"] == "applied"


def test_create_job_missing_fields(logged_in_client):
    response = logged_in_client.post("/api/jobs", json={"company": "Google"})
    assert response.status_code == 400


def test_create_job_invalid_status(logged_in_client):
    response = logged_in_client.post(
        "/api/jobs", json={"company": "Google", "role": "SOC", "status": "bogus"}
    )
    assert response.status_code == 400


def test_update_job_status(logged_in_client):
    create_response = logged_in_client.post(
        "/api/jobs", json={"company": "Google", "role": "SOC Analyst"}
    )
    job_id = create_response.get_json()["job"]["id"]
    response = logged_in_client.put(f"/api/jobs/{job_id}", json={"status": "interview"})
    assert response.status_code == 200
    assert response.get_json()["job"]["status"] == "interview"


def test_delete_job(logged_in_client):
    create_response = logged_in_client.post(
        "/api/jobs", json={"company": "Google", "role": "SOC Analyst"}
    )
    job_id = create_response.get_json()["job"]["id"]
    response = logged_in_client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    get_response = logged_in_client.get(f"/api/jobs/{job_id}")
    assert get_response.status_code == 404


def test_jobs_require_login(client):
    response = client.get("/api/jobs")
    assert response.status_code in (401, 302)


def test_invalid_deadline_format(logged_in_client):
    response = logged_in_client.post(
        "/api/jobs", json={"company": "Google", "role": "SOC", "deadline": "not-a-date"}
    )
    assert response.status_code == 400
