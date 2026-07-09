"""add opportunity intelligence models

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-08 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("headquarters", sa.String(length=255), nullable=True),
        sa.Column("company_size", sa.String(length=100), nullable=True),
        sa.Column("founded_year", sa.Integer(), nullable=True),
        sa.Column("tech_stack", sa.JSON(), nullable=True),
        sa.Column("products", sa.JSON(), nullable=True),
        sa.Column("hiring_trends", sa.Text(), nullable=True),
        sa.Column("recent_news", sa.JSON(), nullable=True),
        sa.Column("interview_difficulty", sa.String(length=50), nullable=True),
        sa.Column("engineering_culture", sa.Text(), nullable=True),
        sa.Column("application_tips", sa.Text(), nullable=True),
        sa.Column("expected_salary", sa.String(length=255), nullable=True),
        sa.Column("interview_process", sa.JSON(), nullable=True),
        sa.Column("linkedin_url", sa.String(length=500), nullable=True),
        sa.Column("glassdoor_rating", sa.Float(), nullable=True),
        sa.Column("indeed_rating", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "market_trends",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trend_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=True),
        sa.Column("growth_pct", sa.Float(), nullable=True),
        sa.Column("period", sa.String(length=50), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "salary_insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("experience_level", sa.String(length=50), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("market_avg", sa.Integer(), nullable=True),
        sa.Column("location_diff", sa.Float(), nullable=True),
        sa.Column("experience_diff", sa.Float(), nullable=True),
        sa.Column("skill_premium", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("company_logo", sa.String(length=500), nullable=True),
        sa.Column("company_url", sa.String(length=500), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("remote_type", sa.String(length=50), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("salary_period", sa.String(length=20), nullable=True),
        sa.Column("employment_type", sa.String(length=50), nullable=True),
        sa.Column("experience_required", sa.Integer(), nullable=True),
        sa.Column("experience_max", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.JSON(), nullable=True),
        sa.Column("responsibilities", sa.JSON(), nullable=True),
        sa.Column("tech_stack", sa.JSON(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), nullable=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("company_profiles.id"), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", "provider", name="uq_external_provider"),
    )
    op.create_table(
        "saved_opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("list_type", sa.String(length=50), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("application_status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity"),
    )
    op.create_table(
        "opportunity_match_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("ats_match", sa.Integer(), nullable=True),
        sa.Column("resume_match", sa.Integer(), nullable=True),
        sa.Column("skill_match", sa.Integer(), nullable=True),
        sa.Column("experience_match", sa.Integer(), nullable=True),
        sa.Column("project_match", sa.Integer(), nullable=True),
        sa.Column("goal_match", sa.Integer(), nullable=True),
        sa.Column("location_match", sa.Integer(), nullable=True),
        sa.Column("salary_match", sa.Integer(), nullable=True),
        sa.Column("explanation", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity_score"),
    )
    op.create_table(
        "opportunity_skill_gaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("missing_skills", sa.JSON(), nullable=True),
        sa.Column("current_skills", sa.JSON(), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("ats_gain_estimates", sa.JSON(), nullable=True),
        sa.Column("coverage_pct", sa.Integer(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity_gap"),
    )
    op.create_table(
        "interview_packs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("likely_questions", sa.JSON(), nullable=True),
        sa.Column("coding_topics", sa.JSON(), nullable=True),
        sa.Column("behavioral_questions", sa.JSON(), nullable=True),
        sa.Column("system_design_topics", sa.JSON(), nullable=True),
        sa.Column("company_questions", sa.JSON(), nullable=True),
        sa.Column("preparation_checklist", sa.JSON(), nullable=True),
        sa.Column("learning_resources", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "opportunity_id", name="uq_user_opportunity_interview"),
    )
    op.create_table(
        "resume_versions_by_company",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("version_name", sa.String(length=100), nullable=True),
        sa.Column("resume_json", sa.JSON(), nullable=False),
        sa.Column("ats_score", sa.Integer(), nullable=True),
        sa.Column("job_description_used", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("resume_versions_by_company")
    op.drop_table("interview_packs")
    op.drop_table("opportunity_skill_gaps")
    op.drop_table("opportunity_match_scores")
    op.drop_table("saved_opportunities")
    op.drop_table("opportunities")
    op.drop_table("salary_insights")
    op.drop_table("market_trends")
    op.drop_table("company_profiles")
