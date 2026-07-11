"""consolidate duplicated models (Job/Opportunity, ResumeVersion)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-11

This migration is part of the Career OS architecture consolidation:
  - `jobs.opportunity_id` links a tracked application back to the
    Opportunity it was discovered from (Job remains the single source
    of truth for application lifecycle/status).
  - `saved_opportunities.applied_at` / `application_status` are dropped;
    that lifecycle now lives exclusively on `Job`.
  - `resume_versions_by_company` is dropped; its data is merged into
    `resume_versions`, which gains `user_id`, `opportunity_id`,
    `company_name`, `ats_score`, `job_description_used` columns.
  - `resume_files.resume_id` links an uploaded file to the structured
    Resume row it was parsed into.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    # --- Job <-> Opportunity link -------------------------------------
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("opportunity_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_jobs_opportunity_id",
            "opportunities",
            ["opportunity_id"],
            ["id"],
        )

    # --- resume_versions: absorb resume_versions_by_company -----------
    with op.batch_alter_table("resume_versions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("opportunity_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("company_name", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("ats_score", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("job_description_used", sa.Text(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_resume_versions_user_id", "users", ["user_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_resume_versions_opportunity_id",
            "opportunities",
            ["opportunity_id"],
            ["id"],
        )

    # Migrate any existing resume_versions_by_company rows into
    # resume_versions before dropping the old table.
    conn = op.get_bind()
    has_old_table = conn.dialect.has_table(conn, "resume_versions_by_company")
    if has_old_table:
        conn.execute(
            sa.text(
                """
                INSERT INTO resume_versions
                    (resume_id, user_id, version_name, snapshot,
                     opportunity_id, company_name, ats_score,
                     job_description_used, created_at)
                SELECT
                    (SELECT id FROM resumes WHERE resumes.user_id = rvbc.user_id LIMIT 1),
                    rvbc.user_id, rvbc.version_name, rvbc.resume_json,
                    rvbc.opportunity_id, rvbc.company_name, rvbc.ats_score,
                    rvbc.job_description_used, rvbc.created_at
                FROM resume_versions_by_company rvbc
                WHERE EXISTS (
                    SELECT 1 FROM resumes WHERE resumes.user_id = rvbc.user_id
                )
                """
            )
        )
        op.drop_table("resume_versions_by_company")

    # --- saved_opportunities: drop duplicated application lifecycle ---
    with op.batch_alter_table("saved_opportunities", schema=None) as batch_op:
        batch_op.drop_column("applied_at")
        batch_op.drop_column("application_status")

    # --- resume_files: link to structured Resume row -------------------
    with op.batch_alter_table("resume_files", schema=None) as batch_op:
        batch_op.add_column(sa.Column("resume_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_resume_files_resume_id", "resumes", ["resume_id"], ["id"]
        )


def downgrade():
    with op.batch_alter_table("resume_files", schema=None) as batch_op:
        batch_op.drop_constraint("fk_resume_files_resume_id", type_="foreignkey")
        batch_op.drop_column("resume_id")

    with op.batch_alter_table("saved_opportunities", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("application_status", sa.String(50), nullable=True)
        )
        batch_op.add_column(sa.Column("applied_at", sa.DateTime(), nullable=True))

    op.create_table(
        "resume_versions_by_company",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "opportunity_id",
            sa.Integer(),
            sa.ForeignKey("opportunities.id"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("version_name", sa.String(100)),
        sa.Column("resume_json", sa.JSON(), nullable=False),
        sa.Column("ats_score", sa.Integer(), nullable=True),
        sa.Column("job_description_used", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
    )

    with op.batch_alter_table("resume_versions", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_resume_versions_opportunity_id", type_="foreignkey"
        )
        batch_op.drop_constraint("fk_resume_versions_user_id", type_="foreignkey")
        batch_op.drop_column("job_description_used")
        batch_op.drop_column("ats_score")
        batch_op.drop_column("company_name")
        batch_op.drop_column("opportunity_id")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_jobs_opportunity_id", type_="foreignkey")
        batch_op.drop_column("opportunity_id")
