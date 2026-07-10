"""add career os models

Revision ID: a1b2c3d4e5f6
Revises: d6e5f4c3b2a1
Create Date: 2026-07-08 21:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "d6e5f4c3b2a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "career_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("target_role", sa.String(length=255), nullable=True),
        sa.Column("target_company", sa.String(length=255), nullable=True),
        sa.Column("target_location", sa.String(length=255), nullable=True),
        sa.Column("target_salary", sa.String(length=100), nullable=True),
        sa.Column("career_level", sa.String(length=50), nullable=True),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("preferred_roles", sa.JSON(), nullable=True),
        sa.Column("preferred_locations", sa.JSON(), nullable=True),
        sa.Column("career_goal_type", sa.String(length=50), nullable=True),
        sa.Column("interests", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "career_goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_role", sa.String(length=255), nullable=True),
        sa.Column("target_company", sa.String(length=255), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_role", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("estimated_weeks", sa.Integer(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "roadmap_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("roadmap_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource_url", sa.String(length=500), nullable=True),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.Column("week", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("skill_tags", sa.JSON(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["roadmap_id"], ["roadmaps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "learning_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=255), nullable=False),
        sa.Column("proficiency", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_name", name="uq_user_skill"),
    )
    op.create_table(
        "skill_graphs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("proficiency", sa.Integer(), nullable=True),
        sa.Column("skill_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category", name="uq_user_category"),
    )
    op.create_table(
        "career_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("score_before", sa.Integer(), nullable=True),
        sa.Column("score_after", sa.Integer(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("achievements", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "career_timeline_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("event_date", sa.DateTime(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ai_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rec_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("impact_score", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("action_link", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_dismissed", sa.Boolean(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "career_score_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("resume_score", sa.Integer(), nullable=True),
        sa.Column("ats_score", sa.Integer(), nullable=True),
        sa.Column("projects_score", sa.Integer(), nullable=True),
        sa.Column("applications_score", sa.Integer(), nullable=True),
        sa.Column("learning_score", sa.Integer(), nullable=True),
        sa.Column("interview_score", sa.Integer(), nullable=True),
        sa.Column("skill_coverage", sa.Integer(), nullable=True),
        sa.Column("breakdown", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("career_score_snapshots")
    op.drop_table("ai_recommendations")
    op.drop_table("career_timeline_events")
    op.drop_table("career_reports")
    op.drop_table("skill_graphs")
    op.drop_table("learning_progress")
    op.drop_table("roadmap_nodes")
    op.drop_table("roadmaps")
    op.drop_table("career_goals")
    op.drop_table("career_profiles")
