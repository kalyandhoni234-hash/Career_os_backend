import logging
from datetime import datetime, timezone

from app.extensions import db

logger = logging.getLogger(__name__)


class RuleExecutionLog(db.Model):
    __tablename__ = "rule_execution_logs"

    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    summary = db.Column(db.Text, nullable=True)
    success = db.Column(db.Boolean, default=True)
    executed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("rule_logs", lazy="dynamic"))
