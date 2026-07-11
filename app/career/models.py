from datetime import datetime, timezone
from app.extensions import db


class CareerProfile(db.Model):
    __tablename__ = "career_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    target_role = db.Column(db.String(255), nullable=True)
    target_company = db.Column(db.String(255), nullable=True)
    target_location = db.Column(db.String(255), nullable=True)
    target_salary = db.Column(db.String(100), nullable=True)
    career_level = db.Column(db.String(50), default="student")
    years_experience = db.Column(db.Integer, default=0)
    company = db.Column(db.String(255), nullable=True)
    position = db.Column(db.String(255), nullable=True)
    employment_type = db.Column(db.String(50), nullable=True)
    preferred_industry = db.Column(db.String(255), nullable=True)
    preferred_country = db.Column(db.String(255), nullable=True)
    work_preference = db.Column(db.String(50), nullable=True)
    career_stage = db.Column(db.String(50), default="student")
    stage_meta = db.Column(db.JSON, default=dict)
    target_joining_year = db.Column(db.Integer, nullable=True)
    preferred_roles = db.Column(db.JSON, default=list)
    preferred_locations = db.Column(db.JSON, default=list)
    career_goal_type = db.Column(db.String(50), default="internship")
    interests = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("career_profile", uselist=False))


class CareerGoal(db.Model):
    __tablename__ = "career_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_role = db.Column(db.String(255), nullable=True)
    target_company = db.Column(db.String(255), nullable=True)
    target_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default="active")
    priority = db.Column(db.Integer, default=3)
    progress = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default="career")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("career_goals", lazy="dynamic"))


class Roadmap(db.Model):
    __tablename__ = "roadmaps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_role = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    estimated_weeks = db.Column(db.Integer, default=12)
    progress = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default="active")
    source = db.Column(db.String(50), default="ai_generated")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("roadmaps", lazy="dynamic"))
    nodes = db.relationship(
        "RoadmapNode",
        backref="roadmap",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="RoadmapNode.order",
    )


class RoadmapNode(db.Model):
    __tablename__ = "roadmap_nodes"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("roadmaps.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    resource_url = db.Column(db.String(500), nullable=True)
    resource_type = db.Column(db.String(50), default="article")
    order = db.Column(db.Integer, default=0)
    week = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default="pending")
    skill_tags = db.Column(db.JSON, default=list)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class LearningProgress(db.Model):
    __tablename__ = "learning_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    skill_name = db.Column(db.String(255), nullable=False)
    proficiency = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100), nullable=True)
    source = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "User", backref=db.backref("learning_progress", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "skill_name", name="uq_user_skill"),
    )


class SkillGraph(db.Model):
    __tablename__ = "skill_graphs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.Integer, default=0)
    skill_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("skill_graphs", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("user_id", "category", name="uq_user_category"),
    )


class CareerReport(db.Model):
    __tablename__ = "career_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    score_before = db.Column(db.Integer, default=0)
    score_after = db.Column(db.Integer, default=0)
    metrics = db.Column(db.JSON, default=dict)
    achievements = db.Column(db.JSON, default=list)
    recommendations = db.Column(db.JSON, default=list)
    summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("career_reports", lazy="dynamic"))


class CareerTimelineEvent(db.Model):
    __tablename__ = "career_timeline_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.DateTime, nullable=False)
    importance = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default="completed")
    tags = db.Column(db.JSON, default=list)
    related_goal_id = db.Column(
        db.Integer, db.ForeignKey("career_goals.id"), nullable=True
    )
    attachment_url = db.Column(db.String(500), nullable=True)
    visibility = db.Column(db.String(50), default="public")
    is_favorite = db.Column(db.Boolean, default=False)
    is_pinned = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    metadata_json = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "User", backref=db.backref("career_timeline_events", lazy="dynamic")
    )
    related_goal = db.relationship(
        "CareerGoal", backref=db.backref("timeline_events", lazy="dynamic")
    )


class TimelineTag(db.Model):
    __tablename__ = "timeline_tags"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), default="#6366f1")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("timeline_tags", lazy="dynamic"))
    __table_args__ = (db.UniqueConstraint("user_id", "name"),)


class TimelineAttachment(db.Model):
    __tablename__ = "timeline_attachments"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer, db.ForeignKey("career_timeline_events.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    file_type = db.Column(db.String(50), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    event = db.relationship(
        "CareerTimelineEvent", backref=db.backref("attachments", lazy="dynamic")
    )
    user = db.relationship(
        "User", backref=db.backref("timeline_attachments", lazy="dynamic")
    )


class AIRecommendation(db.Model):
    __tablename__ = "ai_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rec_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    reasoning = db.Column(db.Text, nullable=True)
    evidence = db.Column(db.Text, nullable=True)
    priority = db.Column(db.Integer, default=3)
    impact_score = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), nullable=True)
    action_link = db.Column(db.String(500), nullable=True)
    metadata_json = db.Column(db.JSON, default=dict)
    is_dismissed = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship(
        "User", backref=db.backref("ai_recommendations", lazy="dynamic")
    )


class UserEducation(db.Model):
    __tablename__ = "user_education"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    institution = db.Column(db.String(255), nullable=False)
    degree = db.Column(db.String(255), nullable=False)
    branch = db.Column(db.String(255), nullable=True)
    specialization = db.Column(db.String(255), nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    current_semester = db.Column(db.Integer, nullable=True)
    cgpa = db.Column(db.Float, nullable=True)
    relevant_coursework = db.Column(db.JSON, default=list)
    achievements = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)
    source = db.Column(db.String(50), default="manual")
    source_id = db.Column(db.String(255), nullable=True)
    confidence = db.Column(db.Float, default=1.0)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "user_education", lazy="dynamic", order_by="UserEducation.order"
        ),
    )


class UserSkill(db.Model):
    __tablename__ = "user_skills"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    experience_level = db.Column(db.String(50), default="beginner")
    years_of_experience = db.Column(db.Float, default=0)
    confidence_rating = db.Column(db.Integer, default=0)
    source = db.Column(db.String(50), default="manual")
    source_id = db.Column(db.String(255), nullable=True)
    confidence = db.Column(db.Float, default=1.0)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("user_skills", lazy="dynamic"))
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_user_skill_name"),
    )


class UserInterest(db.Model):
    __tablename__ = "user_interests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("user_interests", lazy="dynamic"))
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_user_interest_name"),
    )


class UserLanguage(db.Model):
    __tablename__ = "user_languages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    language = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.String(50), default="intermediate")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("user_languages", lazy="dynamic"))
    __table_args__ = (
        db.UniqueConstraint("user_id", "language", name="uq_user_language"),
    )


class SocialLink(db.Model):
    __tablename__ = "social_links"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("social_links", lazy="dynamic"))
    __table_args__ = (
        db.UniqueConstraint("user_id", "platform", name="uq_user_platform"),
    )


class ResumeFile(db.Model):
    __tablename__ = "resume_files"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    file_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("resume_files", lazy="dynamic"))


class UserPreference(db.Model):
    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    job_alerts = db.Column(db.Boolean, default=True)
    weekly_ai_review = db.Column(db.Boolean, default=True)
    email_notifications = db.Column(db.Boolean, default=True)
    public_profile = db.Column(db.Boolean, default=False)
    resume_visibility = db.Column(db.String(50), default="private")
    theme_preference = db.Column(db.String(20), default="system")
    ai_tone = db.Column(db.String(50), default="professional")
    reminder_freq = db.Column(db.String(50), default="weekly")
    weekly_reports = db.Column(db.Boolean, default=True)
    roadmap_gen = db.Column(db.Boolean, default=True)
    daily_motivation = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("preferences", uselist=False))


class CareerScoreSnapshot(db.Model):
    __tablename__ = "career_score_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    overall_score = db.Column(db.Integer, nullable=False)
    resume_score = db.Column(db.Integer, default=0)
    ats_score = db.Column(db.Integer, default=0)
    projects_score = db.Column(db.Integer, default=0)
    applications_score = db.Column(db.Integer, default=0)
    learning_score = db.Column(db.Integer, default=0)
    interview_score = db.Column(db.Integer, default=0)
    skill_coverage = db.Column(db.Integer, default=0)
    breakdown = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship(
        "User", backref=db.backref("career_score_snapshots", lazy="dynamic")
    )
