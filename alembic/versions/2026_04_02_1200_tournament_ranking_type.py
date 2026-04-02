"""Add ranking_type to tournament_types

Revision ID: 2026_04_02_1200
Revises: 2026_04_01_card_theme
Create Date: 2026-04-02 12:00:00.000000

Adds an explicit ranking_type column to tournament_types so the UI can render
Full Results tables without guessing from ad-hoc field values.

  SCORING_ONLY — Swiss, IR formats: rank by score/pts; no W/D/L columns
  WDL_BASED    — League, Group Knockout: rank by win/draw/loss record
"""
from alembic import op
import sqlalchemy as sa


revision = '2026_04_02_1200'
down_revision = '2026_04_01_card_theme'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'tournament_types',
        sa.Column(
            'ranking_type',
            sa.String(20),
            nullable=True,
            comment='SCORING_ONLY or WDL_BASED — drives public standings table format',
        ),
    )
    # Seed known types — safe because unique codes are enforced at bootstrap
    op.execute("UPDATE tournament_types SET ranking_type = 'SCORING_ONLY' WHERE code = 'swiss'")
    op.execute(
        "UPDATE tournament_types SET ranking_type = 'WDL_BASED' "
        "WHERE code IN ('league', 'group_knockout', 'knockout')"
    )


def downgrade():
    op.drop_column('tournament_types', 'ranking_type')
