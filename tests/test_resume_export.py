"""Tests for resume PDF and DOCX export endpoints."""

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
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
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
        json={"email": "exportuser@example.com", "password": "securepass123"},
    )
    client.post(
        "/api/auth/login",
        json={"email": "exportuser@example.com", "password": "securepass123"},
    )
    return client


@pytest.fixture
def seeded_client(logged_in_client):
    logged_in_client.post(
        "/api/resume",
        json={
            "full_name": "Export Test User",
            "email": "export@example.com",
            "phone": "+1-555-0000",
            "location": "Remote",
            "summary": "A seasoned software engineer.",
            "skills": ["Python", "Flask", "PostgreSQL"],
            "experience": [
                {
                    "role": "Software Engineer",
                    "company": "Tech Co",
                    "start": "2020-01",
                    "end": "Present",
                    "bullets": ["Built APIs", "Led team of 3"],
                    "technologies": ["Python", "Flask"],
                }
            ],
            "education": [
                {
                    "school": "State University",
                    "degree": "B.S.",
                    "field": "Computer Science",
                    "start": "2016",
                    "end": "2020",
                }
            ],
            "projects": [
                {
                    "name": "CareerOS",
                    "description": "A career management platform.",
                    "technologies": ["React", "Flask"],
                }
            ],
            "certificates": [
                {"name": "AWS Certified", "issuer": "Amazon", "date": "2023-06"}
            ],
            "languages": [{"name": "English", "level": "Native"}],
        },
    )
    return logged_in_client


# ── Auth guards ──────────────────────────────────────────────


def test_export_requires_login(client):
    resp = client.get("/api/resume/export")
    assert resp.status_code in (401, 302)


def test_export_docx_requires_login(client):
    resp = client.get("/api/resume/export/docx")
    assert resp.status_code in (401, 302)


def test_version_export_requires_login(client):
    resp = client.get("/api/resume/versions/1/export")
    assert resp.status_code in (401, 302)


def test_version_export_docx_requires_login(client):
    resp = client.get("/api/resume/versions/1/export/docx")
    assert resp.status_code in (401, 302)


# ── 404 when no resume exists ────────────────────────────────


def test_export_404_without_resume(logged_in_client):
    resp = logged_in_client.get("/api/resume/export")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "No resume found"


def test_export_docx_404_without_resume(logged_in_client):
    resp = logged_in_client.get("/api/resume/export/docx")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "No resume found"


# ── PDF export ───────────────────────────────────────────────


def test_export_pdf_returns_json_error_when_unavailable(seeded_client, monkeypatch):
    """When WeasyPrint is unavailable the endpoint returns a 503 JSON error."""
    monkeypatch.setattr("app.resume.pdf_engine._weasyprint_available", False)
    resp = seeded_client.get("/api/resume/export")
    assert resp.status_code == 503
    body = resp.get_json()
    assert "error" in body
    assert body["error"] is not None


def test_export_pdf_success(seeded_client):
    """PDF export returns a valid PDF when WeasyPrint is available."""
    resp = seeded_client.get("/api/resume/export")
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.headers["Content-Disposition"].startswith(
        "attachment; filename=Export Test User.pdf"
    )
    assert resp.data.startswith(b"%PDF-1.4")


# ── DOCX export ──────────────────────────────────────────────


def test_export_docx_success(seeded_client):
    resp = seeded_client.get("/api/resume/export/docx")
    assert resp.status_code == 200
    assert (
        resp.content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "attachment; filename=" in resp.headers["Content-Disposition"]
    assert resp.content_length or len(resp.data) > 0
    assert resp.data[:2] == b"PK"  # DOCX is a ZIP archive


# ── Version export ───────────────────────────────────────────


def test_version_export_404_bad_version(seeded_client):
    resp = seeded_client.get("/api/resume/versions/999/export")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Version not found"


def test_version_export_pdf_success(seeded_client):
    """Version PDF export returns a valid PDF when WeasyPrint is available."""
    resp = seeded_client.get("/api/resume/versions/1/export")
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert resp.data.startswith(b"%PDF-1.4")


def test_version_export_docx_success(seeded_client):
    resp = seeded_client.get("/api/resume/versions/1/export/docx")
    assert resp.status_code == 200
    assert (
        resp.content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert resp.data[:2] == b"PK"


# ── PDF health endpoint ──────────────────────────────────────


def test_pdf_health_endpoint(client):
    resp = client.get("/api/resume/pdf-health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "available" in body
    assert "engine" in body
    assert body["engine"] == "weasyprint"
    assert "hint_for_windows" in body
    assert "hint_for_linux" in body
