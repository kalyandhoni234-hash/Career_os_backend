from datetime import datetime, timezone
from app.extensions import db


AGENT_TYPES = [
    "job_discovery",
    "resume_optimization",
    "ats_intelligence",
    "opportunity_ranking",
    "company_intelligence",
    "salary_intelligence",
    "learning",
    "project_recommendation",
    "interview_preparation",
    "networking",
    "notification",
    "weekly_report",
    "career_strategy",
]

AGENT_STATUSES = ["idle", "running", "error", "paused"]
TASK_STATUSES = ["pending", "running", "completed", "failed"]


class CareerAgent(db.Model):
    __tablename__ = "career_agents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="idle")
    last_run_at = db.Column(db.DateTime, nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=True)
    total_runs = db.Column(db.Integer, default=0)
    total_errors = db.Column(db.Integer, default=0)
    config = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("career_agents", lazy="dynamic"))
    tasks = db.relationship(
        "AgentTask", backref="agent", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "agent_type", name="uq_user_agent_type"),
    )


class AgentTask(db.Model):
    __tablename__ = "agent_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("career_agents.id"), nullable=False)
    task_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="pending")
    priority = db.Column(db.Integer, default=3)
    progress = db.Column(db.Integer, default=0)
    input_data = db.Column(db.JSON, default=dict)
    output_data = db.Column(db.JSON, default=dict)
    error_message = db.Column(db.Text, nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("agent_tasks", lazy="dynamic"))
