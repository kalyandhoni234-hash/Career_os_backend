"""add career_stage and stage_meta to career_profiles

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-10 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5a6"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("career_profiles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("career_stage", sa.String(length=50), nullable=True, server_default="student"))
        batch_op.add_column(sa.Column("stage_meta", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("career_profiles", schema=None) as batch_op:
        batch_op.drop_column("stage_meta")
        batch_op.drop_column("career_stage")
