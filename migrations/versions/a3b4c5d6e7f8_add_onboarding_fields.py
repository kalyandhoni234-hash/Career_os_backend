"""add onboarding fields to users, career_profiles, user_preferences

Revision ID: a3b4c5d6e7f8
Revises: 99492d4c5ed8
Create Date: 2026-07-10 21:18:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3b4c5d6e7f8'
down_revision = '99492d4c5ed8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('onboarding_completed', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('onboarding_step', sa.Integer(), nullable=True, server_default='0'))

    with op.batch_alter_table('career_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('position', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('employment_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('preferred_industry', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('preferred_country', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('work_preference', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('target_joining_year', sa.Integer(), nullable=True))

    with op.batch_alter_table('user_preferences', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ai_tone', sa.String(length=50), nullable=True, server_default='professional'))
        batch_op.add_column(sa.Column('reminder_freq', sa.String(length=50), nullable=True, server_default='weekly'))
        batch_op.add_column(sa.Column('weekly_reports', sa.Boolean(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('roadmap_gen', sa.Boolean(), nullable=True, server_default='1'))
        batch_op.add_column(sa.Column('daily_motivation', sa.Boolean(), nullable=True, server_default='1'))


def downgrade():
    with op.batch_alter_table('user_preferences', schema=None) as batch_op:
        batch_op.drop_column('daily_motivation')
        batch_op.drop_column('roadmap_gen')
        batch_op.drop_column('weekly_reports')
        batch_op.drop_column('reminder_freq')
        batch_op.drop_column('ai_tone')

    with op.batch_alter_table('career_profiles', schema=None) as batch_op:
        batch_op.drop_column('target_joining_year')
        batch_op.drop_column('work_preference')
        batch_op.drop_column('preferred_country')
        batch_op.drop_column('preferred_industry')
        batch_op.drop_column('employment_type')
        batch_op.drop_column('position')
        batch_op.drop_column('company')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('onboarding_step')
        batch_op.drop_column('onboarding_completed')
