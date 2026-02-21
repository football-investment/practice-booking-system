"""create_football_skill_assessments_table

Revision ID: ecc960454088
Revises: 41aa88dc98b5
Create Date: 2025-12-02 19:42:00.117235

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ecc960454088'
down_revision = '41aa88dc98b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create football_skill_assessments table
    op.create_table(
        'football_skill_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_license_id', sa.Integer(), nullable=False,
                 comment='Reference to user_licenses (LFA Player specializations)'),
        sa.Column('skill_name', sa.String(50), nullable=False,
                 comment='Skill name: heading, shooting, crossing, passing, dribbling, ball_control'),
        sa.Column('points_earned', sa.Integer(), nullable=False,
                 comment='Points earned in this assessment (e.g., 7)'),
        sa.Column('points_total', sa.Integer(), nullable=False,
                 comment='Total points possible (e.g., 10)'),
        sa.Column('percentage', sa.Float(), nullable=False,
                 comment='Calculated percentage: (points_earned / points_total) * 100'),
        sa.Column('assessed_by', sa.Integer(), nullable=False,
                 comment='Instructor who made this assessment'),
        sa.Column('assessed_at', sa.DateTime(), nullable=False, server_default=sa.func.now(),
                 comment='When this assessment was made'),
        sa.Column('notes', sa.Text(), nullable=True,
                 comment='Optional notes from instructor about this assessment'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for fast queries
    op.create_index('idx_skill_assessments_license', 'football_skill_assessments', ['user_license_id'])
    op.create_index('idx_skill_assessments_skill', 'football_skill_assessments', ['user_license_id', 'skill_name'])

    # Create foreign keys
    op.create_foreign_key(
        'fk_skill_assessments_license',
        'football_skill_assessments', 'user_licenses',
        ['user_license_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_skill_assessments_instructor',
        'football_skill_assessments', 'users',
        ['assessed_by'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Drop foreign keys
    op.drop_constraint('fk_skill_assessments_instructor', 'football_skill_assessments', type_='foreignkey')
    op.drop_constraint('fk_skill_assessments_license', 'football_skill_assessments', type_='foreignkey')

    # Drop indexes
    op.drop_index('idx_skill_assessments_skill', 'football_skill_assessments')
    op.drop_index('idx_skill_assessments_license', 'football_skill_assessments')

    # Drop table
    op.drop_table('football_skill_assessments')