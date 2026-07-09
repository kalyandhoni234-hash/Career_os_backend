"""expand resume model with new fields and versioning

Revision ID: d6e5f4c3b2a1
Revises: f1c2a3b4d5e6
Create Date: 2026-07-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd6e5f4c3b2a1'
down_revision = 'f1c2a3b4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('resume_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=False),
        sa.Column('version_name', sa.String(length=100), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('resumes', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('resumes', sa.Column('website', sa.String(length=500), nullable=True))
    op.add_column('resumes', sa.Column('linkedin', sa.String(length=500), nullable=True))
    op.add_column('resumes', sa.Column('github', sa.String(length=500), nullable=True))
    op.add_column('resumes', sa.Column('portfolio', sa.String(length=500), nullable=True))
    op.add_column('resumes', sa.Column('certificates', sa.JSON(), nullable=True))
    op.add_column('resumes', sa.Column('achievements', sa.JSON(), nullable=True))
    op.add_column('resumes', sa.Column('languages', sa.JSON(), nullable=True))
    op.add_column('resumes', sa.Column('publications', sa.JSON(), nullable=True))
    op.add_column('resumes', sa.Column('tone', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('resumes', 'tone')
    op.drop_column('resumes', 'publications')
    op.drop_column('resumes', 'languages')
    op.drop_column('resumes', 'achievements')
    op.drop_column('resumes', 'certificates')
    op.drop_column('resumes', 'portfolio')
    op.drop_column('resumes', 'github')
    op.drop_column('resumes', 'linkedin')
    op.drop_column('resumes', 'website')
    op.drop_column('resumes', 'title')
    op.drop_table('resume_versions')
