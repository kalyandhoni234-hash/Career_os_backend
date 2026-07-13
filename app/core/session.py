"""Safe database session commit and rollback utilities.

Every function that writes to the database MUST use one of these helpers
instead of calling db.session.commit() directly.  This guarantees that a
failed transaction is always rolled back so the session does not become
poisoned for subsequent requests.
"""

import logging
from typing import Optional

from app.extensions import db

logger = logging.getLogger(__name__)


def safe_commit() -> None:
    """Commit the current transaction with automatic rollback on failure.

    Call this instead of ``db.session.commit()`` everywhere.

    Raises the original exception so callers can handle it if needed;
    the session is always restored to a clean state first.
    """
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Database commit failed — session rolled back")
        raise


def safe_delete(db_object) -> None:
    """Delete *db_object* and commit, rolling back on failure."""
    try:
        db.session.delete(db_object)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Database delete failed — session rolled back")
        raise


def rollback_on_error(func):
    """Decorator that rolls back the session if *func* raises.

    This is useful for service-layer functions that perform multiple
    database writes and want to keep the session clean on failure
    without catching every exception individually.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            db.session.rollback()
            raise
    return wrapper
