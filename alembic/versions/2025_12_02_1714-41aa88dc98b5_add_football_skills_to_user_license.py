"""add_football_skills_to_user_license

Revision ID: 41aa88dc98b5
Revises: cf7bf280ac2a
Create Date: 2025-12-02 17:14:19.790259

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '41aa88dc98b5'
down_revision = 'cf7bf280ac2a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add football_skills JSON column for LFA Player skill tracking
    op.add_column('user_licenses',
                  sa.Column('football_skills', sa.JSON(), nullable=True,
                           comment='6 football skill percentages for LFA Player specializations (heading, shooting, crossing, passing, dribbling, ball_control)'))

    # Add skills_last_updated_at timestamp
    op.add_column('user_licenses',
                  sa.Column('skills_last_updated_at', sa.DateTime(), nullable=True,
                           comment='When skills were last updated'))

    # Add skills_updated_by foreign key
    op.add_column('user_licenses',
                  sa.Column('skills_updated_by', sa.Integer(), nullable=True,
                           comment='Instructor who last updated skills'))
    op.create_foreign_key('fk_user_licenses_skills_updated_by',
                         'user_licenses', 'users',
                         ['skills_updated_by'], ['id'],
                         ondelete='SET NULL')


def downgrade() -> None:
    # Drop foreign key and columns
    op.drop_constraint('fk_user_licenses_skills_updated_by', 'user_licenses', type_='foreignkey')
    op.drop_column('user_licenses', 'skills_updated_by')
    op.drop_column('user_licenses', 'skills_last_updated_at')
    op.drop_column('user_licenses', 'football_skills')