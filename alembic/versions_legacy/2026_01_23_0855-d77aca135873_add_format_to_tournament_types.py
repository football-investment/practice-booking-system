"""add_format_to_tournament_types

Revision ID: d77aca135873
Revises: 7e4d1320e6a4
Create Date: 2026-01-23 08:55:21.261727

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd77aca135873'
down_revision = '7e4d1320e6a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add format column to tournament_types
    op.add_column('tournament_types', sa.Column(
        'format',
        sa.String(50),
        nullable=False,
        server_default='INDIVIDUAL_RANKING',
        comment='Match format: INDIVIDUAL_RANKING (multi-player ranking) or HEAD_TO_HEAD (1v1 or team vs team score-based)'
    ))


def downgrade() -> None:
    op.drop_column('tournament_types', 'format')