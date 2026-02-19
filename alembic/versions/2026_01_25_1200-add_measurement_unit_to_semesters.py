"""add_measurement_unit_to_semesters

Revision ID: 2026_01_25_1200
Revises: 2026_01_23_1830
Create Date: 2026-01-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_01_25_1200'
down_revision = 'add_scoring_type_002'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add measurement_unit column to semesters table.

    measurement_unit stores the unit of measurement for INDIVIDUAL_RANKING tournaments:
    - TIME_BASED: 'seconds', 'minutes', 'hours'
    - DISTANCE_BASED: 'meters', 'centimeters', 'kilometers'
    - SCORE_BASED: 'points', 'repetitions', 'goals'
    - PLACEMENT: NULL (not applicable)
    """
    op.add_column('semesters', sa.Column('measurement_unit', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('semesters', 'measurement_unit')
