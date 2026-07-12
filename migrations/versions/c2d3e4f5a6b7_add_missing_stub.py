"""c2d3e4f5a6b7 - empty no-op migration to satisfy Render DB history

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-11 00:00:00.000000

This migration is a no-op placeholder created to match the alembic_version
entry on the Render database. The actual migration file was lost from version
control but the revision was already stamped, causing:
  ERROR [flask_migrate] Error: Can't locate revision identified by 'c2d3e4f5a6b7'
"""


revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
