from datetime import datetime, timezone
from app.extensions import db


class Opportunity(db.Model):
    __tablename__ = "opportunities"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(255), nullable=True)
    provider = db.Column(db.String(100), default="manual")
    url = db.Column(db.String(500), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    company_logo = db.Column(db.String(500), nullable=True)
    company_url = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    remote_type = db.Column(db.String(50), nullable=True)
    salary_min = db.Column(db.Integer, nullable=True)
    salary_max = db.Column(db.Integer, nullable=True)
    currency = db.Column(db.String(10), default="INR")
    salary_period = db.Column(db.String(20), default="yearly")
    employment_type = db.Column(db.String(50), default="full-time")
    experience_required = db.Column(db.Integer, nullable=True)
    experience_max = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.JSON, default=list)
    responsibilities = db.Column(db.JSON, default=list)
    tech_stack = db.Column(db.JSON, default=list)
    posted_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    scraped_at = db.Column(db.DateTime, nullable=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("company_profiles.id"), nullable=True
    )
    raw_data = db.Column(db.JSON, default=dict)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    company = db.relationship(
        "CompanyProfile", backref=db.backref("opportunities", lazy="dynamic")
    )
    saved_by_users = db.relationship(
        "SavedOpportunity",
        backref="opportunity",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.UniqueConstraint("external_id", "provider", name="uq_external_provider"),
    )


class CompanyProfile(db.Model):
    __tablename__ = "company_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    logo_url = db.Column(db.String(500), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    industry = db.Column(db.String(255), nullable=True)
    headquarters = db.Column(db.String(255), nullable=True)
    company_size = db.Column(db.String(100), nullable=True)
    founded_year = db.Column(db.Integer, nullable=True)
    tech_stack = db.Column(db.JSON, default=list)
    products = db.Column(db.JSON, default=list)
    hiring_trends = db.Column(db.Text, nullable=True)
    recent_news = db.Column(db.JSON, default=list)
    interview_difficulty = db.Column(db.String(50), nullable=True)
    engineering_culture = db.Column(db.Text, nullable=True)
    application_tips = db.Column(db.Text, nullable=True)
    expected_salary = db.Column(db.String(255), nullable=True)
    interview_process = db.Column(db.JSON, default=list)
    linkedin_url = db.Column(db.String(500), nullable=True)
    glassdoor_rating = db.Column(db.Float, nullable=True)
    indeed_rating = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SavedOpportunity(db.Model):
    __tablename__ = "saved_opportunities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=False
    )
    list_type = db.Column(db.String(50), default="saved")
    tags = db.Column(db.JSON, default=list)
    notes = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, nullable=True)
    application_status = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "User", backref=db.backref("saved_opportunities", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity"),
    )


class OpportunityMatchScore(db.Model):
    __tablename__ = "opportunity_match_scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=False
    )
    overall_score = db.Column(db.Integer, default=0)
    ats_match = db.Column(db.Integer, default=0)
    resume_match = db.Column(db.Integer, default=0)
    skill_match = db.Column(db.Integer, default=0)
    experience_match = db.Column(db.Integer, default=0)
    project_match = db.Column(db.Integer, default=0)
    goal_match = db.Column(db.Integer, default=0)
    location_match = db.Column(db.Integer, default=0)
    salary_match = db.Column(db.Integer, default=0)
    explanation = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship(
        "User", backref=db.backref("opportunity_match_scores", lazy="dynamic")
    )
    opportunity = db.relationship(
        "Opportunity", backref=db.backref("match_scores", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "opportunity_id", name="uq_user_opportunity_score"
        ),
    )


class OpportunitySkillGap(db.Model):
    __tablename__ = "opportunity_skill_gaps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=False
    )
    missing_skills = db.Column(db.JSON, default=list)
    current_skills = db.Column(db.JSON, default=list)
    required_skills = db.Column(db.JSON, default=list)
    ats_gain_estimates = db.Column(db.JSON, default=dict)
    coverage_pct = db.Column(db.Integer, default=0)
    priority = db.Column(db.String(20), default="medium")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship(
        "User", backref=db.backref("opportunity_skill_gaps", lazy="dynamic")
    )
    opportunity = db.relationship(
        "Opportunity", backref=db.backref("skill_gaps", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "opportunity_id", name="uq_user_opportunity_gap"
        ),
    )


class SalaryInsight(db.Model):
    __tablename__ = "salary_insights"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    experience_level = db.Column(db.String(50), nullable=True)
    salary_min = db.Column(db.Integer, nullable=True)
    salary_max = db.Column(db.Integer, nullable=True)
    currency = db.Column(db.String(10), default="INR")
    market_avg = db.Column(db.Integer, nullable=True)
    location_diff = db.Column(db.Float, nullable=True)
    experience_diff = db.Column(db.Float, nullable=True)
    skill_premium = db.Column(db.JSON, default=dict)
    confidence = db.Column(db.Integer, default=50)
    source = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class MarketTrend(db.Model):
    __tablename__ = "market_trends"

    id = db.Column(db.Integer, primary_key=True)
    trend_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    value = db.Column(db.String(255), nullable=True)
    growth_pct = db.Column(db.Float, nullable=True)
    period = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    source = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class InterviewPack(db.Model):
    __tablename__ = "interview_packs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=False
    )
    likely_questions = db.Column(db.JSON, default=list)
    coding_topics = db.Column(db.JSON, default=list)
    behavioral_questions = db.Column(db.JSON, default=list)
    system_design_topics = db.Column(db.JSON, default=list)
    company_questions = db.Column(db.JSON, default=list)
    preparation_checklist = db.Column(db.JSON, default=list)
    learning_resources = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship(
        "User", backref=db.backref("interview_packs", lazy="dynamic")
    )
    opportunity = db.relationship(
        "Opportunity", backref=db.backref("interview_packs", lazy="dynamic")
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "opportunity_id", name="uq_user_opportunity_interview"
        ),
    )


class ResumeVersionByCompany(db.Model):
    __tablename__ = "resume_versions_by_company"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(
        db.Integer, db.ForeignKey("opportunities.id"), nullable=False
    )
    company_name = db.Column(db.String(255), nullable=False)
    version_name = db.Column(db.String(100), default="v1")
    resume_json = db.Column(db.JSON, nullable=False)
    ats_score = db.Column(db.Integer, nullable=True)
    job_description_used = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship(
        "User", backref=db.backref("resume_versions_by_company", lazy="dynamic")
    )
    opportunity = db.relationship(
        "Opportunity", backref=db.backref("resume_versions", lazy="dynamic")
    )
