"""add_match_structure_fields_to_sessions

Revision ID: 98e008cea123
Revises: 618a1eb1eea8
Create Date: 2026-01-22 12:27:41.604191

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98e008cea123'
down_revision = '618a1eb1eea8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add match structure fields to sessions table
    op.add_column('sessions', sa.Column('match_format', sa.String(50), nullable=True,
        comment='Match format type: INDIVIDUAL_RANKING, HEAD_TO_HEAD, TEAM_MATCH, TIME_BASED, SKILL_RATING'))
    op.add_column('sessions', sa.Column('scoring_type', sa.String(50), nullable=True,
        comment='Scoring type: PLACEMENT, WIN_LOSS, SCORE_BASED, TIME_BASED, SKILL_RATING'))
    op.add_column('sessions', sa.Column('structure_config', sa.JSON(), nullable=True,
        comment='Match structure configuration (pairings, teams, performance criteria)'))


def downgrade() -> None:
    # Remove match structure fields from sessions table
    op.drop_column('sessions', 'structure_config')
    op.drop_column('sessions', 'scoring_type')
    op.drop_column('sessions', 'match_format')