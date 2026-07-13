"""Tests for the three failing endpoints and their root causes."""
import pytest
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db, bcrypt


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        "WTF_CSRF_ENABLED": True,
        "SECRET_KEY": "fixed-test-secret-for-csrf",
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
    pw = bcrypt.generate_password_hash("securepass123").decode("utf-8")
    with db.session.begin():
        from app.auth.models import User
        u = User(email="test@example.com", password_hash=pw)
        db.session.add(u)
    client.post("/api/auth/login", json={"email": "test@example.com", "password": "securepass123"})
    return client


@pytest.fixture
def seeded_client(logged_in_client, app):
    """Client with profile, career profile, resume, and jobs."""
    with app.app_context():
        from app.auth.models import User
        from app.users.models import Profile
        from app.resume.models import Resume
        from app.career.models import CareerProfile
        from app.jobs.models import Job

        user = User.query.filter_by(email="test@example.com").first()
        uid = user.id

        p = Profile(user_id=uid, first_name="Test", last_name="User",
                     skills=["Python", "JavaScript"], education="BS CS")
        cp = CareerProfile(user_id=uid, target_role="Software Engineer",
                           career_level="mid", years_experience=3)
        r = Resume(user_id=uid, full_name="Test User", title="Software Engineer",
                   summary="Experienced dev", skills=["Python", "JavaScript"])
        j1 = Job(user_id=uid, company="Acme", role="Engineer", status="applied")
        j2 = Job(user_id=uid, company="Globex", role="Dev", status="interview")
        db.session.add_all([p, cp, r, j1, j2])
        db.session.commit()
    return logged_in_client


def _get_csrf(client):
    """Get CSRF token and cookie for the test client."""
    r = client.get("/api/auth/csrf-token")
    data = r.get_json()
    token = data["csrf_token"]
    cookie_header = r.headers.get("Set-Cookie", "")
    cookie_val = None
    if "csrf_token=" in cookie_header:
        cookie_val = cookie_header.split("csrf_token=")[1].split(";")[0]
    return token, cookie_val


class TestRecommendationDeduplication:
    """GET /api/career/recommendations should not create duplicate records."""

    def test_returns_same_recs_on_repeat_calls(self, seeded_client):
        from app.career.models import AIRecommendation

        r1 = seeded_client.get("/api/career/recommendations")
        assert r1.status_code == 200
        count1 = AIRecommendation.query.filter_by(
            is_dismissed=False, is_completed=False
        ).count()
        assert count1 > 0, "First call should create recommendations"

        r2 = seeded_client.get("/api/career/recommendations")
        assert r2.status_code == 200
        count2 = AIRecommendation.query.filter_by(
            is_dismissed=False, is_completed=False
        ).count()

        assert count1 == count2, f"Duplicate recs created: {count1} -> {count2}"

    def test_flush_error_does_not_poison_session(self, seeded_client):
        from app.career.models import AIRecommendation
        from unittest.mock import patch

        call_count = 0
        original_flush = db.session.flush

        def failing_flush():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Simulated flush failure")
            return original_flush()

        with patch.object(db.session, "flush", side_effect=failing_flush):
            r = seeded_client.get("/api/career/recommendations")
            assert r.status_code in (200, 500)

        r2 = seeded_client.get("/api/auth/me")
        assert r2.status_code == 200, "Session poisoned after flush failure"


class TestRoadmapMatching:
    """POST /api/career/roadmaps/auto-generate should find a roadmap for common role names."""

    def test_software_engineer_matches_full_stack(self, seeded_client):
        token, cookie = _get_csrf(seeded_client)
        r = seeded_client.post(
            "/api/career/roadmaps/auto-generate",
            json={"target_role": "Software Engineer"},
            headers={"X-CSRF-Token": token},
        )
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert data["roadmap"]["category"] == "full_stack_developer"

    def test_full_stack_developer_matches(self, seeded_client):
        token, cookie = _get_csrf(seeded_client)
        r = seeded_client.post(
            "/api/career/roadmaps/auto-generate",
            json={"target_role": "Full Stack Developer"},
            headers={"X-CSRF-Token": token},
        )
        assert r.status_code == 201

    def test_unknown_role_returns_400(self, seeded_client):
        token, cookie = _get_csrf(seeded_client)
        r = seeded_client.post(
            "/api/career/roadmaps/auto-generate",
            json={"target_role": "Underwater Basket Weaver"},
            headers={"X-CSRF-Token": token},
        )
        assert r.status_code == 400

    def test_no_role_and_no_profile_returns_400(self, client):
        pw = bcrypt.generate_password_hash("pass12345").decode("utf-8")
        with db.session.begin():
            from app.auth.models import User
            u = User(email="norole@test.com", password_hash=pw)
            db.session.add(u)
        client.post("/api/auth/login", json={"email": "norole@test.com", "password": "pass12345"})
        token, _ = _get_csrf(client)
        r = client.post(
            "/api/career/roadmaps/auto-generate",
            json={},
            headers={"X-CSRF-Token": token},
        )
        assert r.status_code == 400


class TestCSRFReturnsJSON:
    """All CSRF 403 responses must be JSON, never HTML."""

    def test_missing_csrf_returns_json(self, logged_in_client):
        r = logged_in_client.post(
            "/api/career/roadmaps/auto-generate",
            json={"target_role": "Software Engineer"},
        )
        assert r.status_code == 403
        data = r.get_json()
        assert data is not None, "CSRF error returned HTML instead of JSON"
        assert data["code"] == "INVALID_CSRF_TOKEN"

    def test_invalid_csrf_returns_json(self, logged_in_client):
        r = logged_in_client.post(
            "/api/career/roadmaps/auto-generate",
            json={"target_role": "Software Engineer"},
            headers={"X-CSRF-Token": "garbage-token"},
        )
        assert r.status_code == 403
        data = r.get_json()
        assert data is not None, "CSRF error returned HTML instead of JSON"

    def test_valid_csrf_passes(self, seeded_client):
        token, _ = _get_csrf(seeded_client)
        r = seeded_client.post(
            "/api/career/roadmaps/auto-generate",
            json={"target_role": "Software Engineer"},
            headers={"X-CSRF-Token": token},
        )
        assert r.status_code in (200, 201, 400), f"Expected 200/201/400, got {r.status_code}"


class TestAgentActionsIsReadOnly:
    """GET /api/opportunities/agent/actions must not write to the database."""

    def test_returns_200_for_new_user(self, seeded_client):
        r = seeded_client.get("/api/opportunities/agent/actions")
        assert r.status_code == 200
        data = r.get_json()
        assert "agent" in data

    def test_no_new_records_created(self, seeded_client):
        from app.agents.models import AgentTask

        before = AgentTask.query.count()
        seeded_client.get("/api/opportunities/agent/actions")
        after = AgentTask.query.count()
        assert before == after, "Agent actions endpoint created records in DB"

    def test_session_survives_after_agent_actions(self, seeded_client):
        seeded_client.get("/api/opportunities/agent/actions")
        r = seeded_client.get("/api/auth/me")
        assert r.status_code == 200


class TestSessionPoisoningRecovery:
    """Verify that a poisoned session from one request doesn't kill the next."""

    def test_recommendation_write_failure_does_not_block_subsequent_requests(self, seeded_client):
        from unittest.mock import patch

        with patch("app.career.services.recommendation_service.safe_commit",
                    side_effect=Exception("Simulated commit failure")):
            r = seeded_client.get("/api/career/recommendations")
            assert r.status_code == 500

        r2 = seeded_client.get("/api/opportunities/agent/actions")
        assert r2.status_code == 200, "Session poisoned by failed recommendation commit"

        r3 = seeded_client.get("/api/career/recommendations")
        assert r3.status_code == 200, "Session still poisoned on second attempt"
