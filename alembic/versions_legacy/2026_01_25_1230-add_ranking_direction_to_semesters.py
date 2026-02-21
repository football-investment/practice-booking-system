"""add_ranking_direction_to_semesters

Revision ID: 2026_01_25_1230
Revises: 2026_01_25_1200
Create Date: 2026-01-25 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_01_25_1230'
down_revision = '2026_01_25_1200'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add ranking_direction column to semesters table.

    ranking_direction stores the ranking order for INDIVIDUAL_RANKING tournaments:
    - ASC: Ascending (lowest value wins) - e.g., 100m sprint (10.5s < 11.2s)
    - DESC: Descending (highest value wins) - e.g., plank hold (120s > 90s)

    HEAD_TO_HEAD: Always DESC (highest score wins)
    PLACEMENT: NULL (not applicable)
    """
    op.add_column('semesters', sa.Column('ranking_direction', sa.String(10), nullable=True))

    # Set default to DESC for existing tournaments
    op.execute("UPDATE semesters SET ranking_direction = 'DESC' WHERE format = 'INDIVIDUAL_RANKING'")


def downgrade():
    op.drop_column('semesters', 'ranking_direction')
