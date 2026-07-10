"""add job fields (priority, next_action, resume_version, ats_score, location)

Revision ID: f1c2a3b4d5e6
Revises: eea9172a6ec5
Create Date: 2026-07-08 16:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1c2a3b4d5e6"
down_revision = "eea9172a6ec5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("priority", sa.String(length=20), nullable=True))
    op.add_column(
        "jobs", sa.Column("next_action", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "jobs", sa.Column("resume_version", sa.String(length=50), nullable=True)
    )
    op.add_column("jobs", sa.Column("ats_score", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("location", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("jobs", "location")
    op.drop_column("jobs", "ats_score")
    op.drop_column("jobs", "resume_version")
    op.drop_column("jobs", "next_action")
    op.drop_column("jobs", "priority")
