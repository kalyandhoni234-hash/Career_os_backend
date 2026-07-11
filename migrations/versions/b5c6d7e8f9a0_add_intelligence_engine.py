"""add intelligence engine models and source tracking columns

Revision ID: b5c6d7e8f9a0
Revises: a3b4c5d6e7f8
Create Date: 2026-07-10 21:38:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5c6d7e8f9a0'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    # New canonical tables
    op.create_table(
        'canonical_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('repo_url', sa.String(length=500), nullable=True),
        sa.Column('primary_language', sa.String(length=100), nullable=True),
        sa.Column('languages', sa.JSON(), nullable=True),
        sa.Column('stars', sa.Integer(), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=True),
        sa.Column('is_fork', sa.Boolean(), nullable=True),
        sa.Column('topics', sa.JSON(), nullable=True),
        sa.Column('readme_url', sa.String(length=500), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'source', 'source_id', name='uq_project_source'),
    )
    op.create_table(
        'canonical_experience',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.String(length=20), nullable=True),
        sa.Column('end_date', sa.String(length=20), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=True),
        sa.Column('technologies', sa.JSON(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'source', 'source_id', name='uq_experience_source'),
    )
    op.create_table(
        'canonical_certificates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('issuer', sa.String(length=255), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('issue_date', sa.String(length=20), nullable=True),
        sa.Column('expiry_date', sa.String(length=20), nullable=True),
        sa.Column('credential_id', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'career_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_source', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Source tracking columns on existing tables
    with op.batch_alter_table('user_skills', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', sa.String(length=50), nullable=True, server_default='manual'))
        batch_op.add_column(sa.Column('source_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True, server_default='1.0'))
        batch_op.add_column(sa.Column('last_synced_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('user_education', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', sa.String(length=50), nullable=True, server_default='manual'))
        batch_op.add_column(sa.Column('source_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True, server_default='1.0'))
        batch_op.add_column(sa.Column('last_synced_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_education', schema=None) as batch_op:
        batch_op.drop_column('last_synced_at')
        batch_op.drop_column('confidence')
        batch_op.drop_column('source_id')
        batch_op.drop_column('source')

    with op.batch_alter_table('user_skills', schema=None) as batch_op:
        batch_op.drop_column('last_synced_at')
        batch_op.drop_column('confidence')
        batch_op.drop_column('source_id')
        batch_op.drop_column('source')

    op.drop_table('career_events')
    op.drop_table('canonical_certificates')
    op.drop_table('canonical_experience')
    op.drop_table('canonical_projects')
