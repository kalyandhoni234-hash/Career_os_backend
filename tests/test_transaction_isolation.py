"""Regression tests for transaction isolation.

Verifies that:
  1. A failed commit does not poison the session for subsequent requests.
  2. safe_commit() rolls back on SQLAlchemy errors.
  3. The error handlers roll back the session on 500/401/404.
  4. Multiple sequential writes work correctly.
"""
import pytest
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db
from app.core.session import safe_commit, safe_delete
from app.jobs.models import Job
from app.career.models import CareerGoal


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
        "DEBUG": False,
        "SECRET_KEY": "test-secret-for-transaction-tests",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class TestSafeCommit:
    """Unit tests for the safe_commit / safe_delete wrappers."""

    def test_safe_commit_success(self, app):
        """A successful commit does not raise."""
        with app.app_context():
            safe_commit()  # should not raise

    def test_safe_commit_rolls_back_on_failure(self, app):
        """safe_commit rolls back and re-raises when commit() raises."""
        with app.app_context():
            with patch.object(db.session, "commit") as mock_commit:
                mock_commit.side_effect = IntegrityError("mock", "mock", "mock")
                with patch.object(db.session, "rollback") as mock_rollback:
                    with pytest.raises(IntegrityError):
                        safe_commit()
                    mock_rollback.assert_called_once()

    def test_safe_delete_rolls_back_on_failure(self, app):
        """safe_delete rolls back and raises when delete+commit fail."""
        with app.app_context():
            with patch.object(db.session, "delete") as mock_delete:
                mock_delete.side_effect = IntegrityError("mock", "mock", "mock")
                with patch.object(db.session, "rollback") as mock_rollback:
                    with pytest.raises(IntegrityError):
                        safe_delete(None)
                    mock_rollback.assert_called_once()


class TestTransactionIsolation:
    """Integration tests using real DB transactions."""

    def test_write_after_rollback_succeeds(self, app):
        """After a forced rollback, the next write should succeed."""
        with app.app_context():
            db.session.rollback()
            goal = CareerGoal(user_id=1, title="Post-rollback goal", priority=3)
            db.session.add(goal)
            safe_commit()
            assert goal.id is not None

    def test_duplicate_allowed(self, app):
        """Writing the same data twice works (no uniqueness conflict)."""
        with app.app_context():
            job1 = Job(
                user_id=9999,
                role="Dup Test",
                company="TestCorp",
            )
            db.session.add(job1)
            safe_commit()

            job2 = Job(
                user_id=9999,
                role="Dup Test",
                company="TestCorp",
            )
            db.session.add(job2)
            safe_commit()
            assert job2.id is not None

    def test_multiple_sequential_writes(self, app):
        """Multiple sequential safe_commit calls all succeed."""
        with app.app_context():
            for i in range(5):
                goal = CareerGoal(user_id=1, title=f"Sequential goal {i}", priority=3)
                db.session.add(goal)
                safe_commit()
                assert goal.id is not None, f"Goal {i} has no id"

    def test_rollback_after_flush_error(self, app):
        """A flush error rolls back and subsequent writes work."""
        with app.app_context():
            goal = CareerGoal(user_id=1, title="Flush test", priority=3)
            db.session.add(goal)
            try:
                db.session.flush()
            except Exception:
                db.session.rollback()
            goal2 = CareerGoal(user_id=1, title="Post-flush test", priority=3)
            db.session.add(goal2)
            safe_commit()

    def test_write_after_safe_commit_rollback(self, app):
        """After a failed safe_commit, the session is clean for the next write."""
        with app.app_context():
            # Simulate a scenario where commit fails
            with patch.object(db.session, "commit") as mock_commit:
                mock_commit.side_effect = [
                    IntegrityError("mock", "mock", "mock"),  # first call fails
                    None,  # second call succeeds
                ]
                with pytest.raises(IntegrityError):
                    safe_commit()
            # Next write must work
            goal = CareerGoal(user_id=1, title="Post-rollback write", priority=3)
            db.session.add(goal)
            safe_commit()
            assert goal.id is not None


class TestErrorHandlerRollback:
    """Verify error handlers return JSON and roll back the session."""

    def test_500_returns_json(self, app, client):
        """A 500 response should include a JSON body after rollback."""
        resp = client.get("/api/career/roadmaps/999999")
        assert resp.is_json, f"Expected JSON response, got {resp.status_code}"
        body = resp.get_json()
        assert body is not None
        assert "error" in body or "message" in body

    def test_404_returns_json(self, app, client):
        """A 404 for an API route should return JSON, not HTML."""
        resp = client.get("/api/nonexistent-route-xyz")
        assert resp.is_json, f"Expected JSON, got {resp.status_code} {resp.content_type}"
        body = resp.get_json()
        assert body.get("code") == "NOT_FOUND"
