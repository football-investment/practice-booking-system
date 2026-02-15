"""add_skill_rating_delta_to_tournament_participations

Revision ID: d3e9f1a2b4c5
Revises: cf7ccbb08eaa
Create Date: 2026-02-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd3e9f1a2b4c5'
down_revision = 'cf7ccbb08eaa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tournament_participations',
        sa.Column(
            'skill_rating_delta',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='V3 EMA per-tournament rating delta: {"passing": 1.2, "dribbling": -0.4}. '
                    'Isolated to this tournament only. Written at reward distribution time.',
        ),
    )


def downgrade() -> None:
    op.drop_column('tournament_participations', 'skill_rating_delta')
