"""add onboarding and motivation fields to user_licenses

Revision ID: add_onboarding_motivation
Revises: add_instructor_materials
Create Date: 2025-11-27 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_onboarding_motivation'
down_revision = 'add_instructor_materials'
branch_labels = None
depends_on = None


def upgrade():
    """Add onboarding and motivation tracking fields to user_licenses table"""

    # Add onboarding fields
    op.add_column('user_licenses', sa.Column(
        'onboarding_completed',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='Whether student completed basic onboarding for this specialization'
    ))

    op.add_column('user_licenses', sa.Column(
        'onboarding_completed_at',
        sa.DateTime(),
        nullable=True,
        comment='When student completed onboarding'
    ))

    # Add motivation scoring fields (admin/instructor only)
    op.add_column('user_licenses', sa.Column(
        'motivation_scores',
        postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
        comment='Motivation assessment scores (1-5 scale) - filled by admin/instructor'
    ))

    op.add_column('user_licenses', sa.Column(
        'average_motivation_score',
        sa.Float(),
        nullable=True,
        comment='Calculated average motivation score (1.0-5.0)'
    ))

    op.add_column('user_licenses', sa.Column(
        'motivation_last_assessed_at',
        sa.DateTime(),
        nullable=True,
        comment='When motivation was last assessed'
    ))

    op.add_column('user_licenses', sa.Column(
        'motivation_assessed_by',
        sa.Integer(),
        nullable=True,
        comment='Admin/instructor who assessed motivation'
    ))

    # Add foreign key constraint for motivation_assessed_by
    op.create_foreign_key(
        'fk_user_licenses_motivation_assessed_by',
        'user_licenses',
        'users',
        ['motivation_assessed_by'],
        ['id']
    )


def downgrade():
    """Remove onboarding and motivation tracking fields"""

    # Drop foreign key first
    op.drop_constraint('fk_user_licenses_motivation_assessed_by', 'user_licenses', type_='foreignkey')

    # Drop all added columns
    op.drop_column('user_licenses', 'motivation_assessed_by')
    op.drop_column('user_licenses', 'motivation_last_assessed_at')
    op.drop_column('user_licenses', 'average_motivation_score')
    op.drop_column('user_licenses', 'motivation_scores')
    op.drop_column('user_licenses', 'onboarding_completed_at')
    op.drop_column('user_licenses', 'onboarding_completed')
