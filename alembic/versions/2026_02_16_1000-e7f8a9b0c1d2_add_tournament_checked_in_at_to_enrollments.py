"""add_tournament_checked_in_at_to_enrollments

Revision ID: e7f8a9b0c1d2
Revises: d3e9f1a2b4c5
Create Date: 2026-02-16 10:00:00.000000

Regression fix: pre-tournament check-in was decoupled from bracket generation
during tournament session generator decomposition (commit 812512c).

This migration adds tournament_checked_in_at to semester_enrollments so that:
- Players can confirm pre-tournament attendance via the check-in endpoint
- generate_sessions() seeds brackets from confirmed players only
- NULL = not checked in (backward compatible: existing rows unaffected)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'd3e9f1a2b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'semester_enrollments',
        sa.Column(
            'tournament_checked_in_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when player confirmed tournament attendance (pre-tournament check-in)',
        ),
    )
    # Index for fast "who has checked in?" lookups during bracket generation
    op.create_index(
        'ix_semester_enrollments_tournament_checked_in_at',
        'semester_enrollments',
        ['tournament_checked_in_at'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_semester_enrollments_tournament_checked_in_at',
        table_name='semester_enrollments',
    )
    op.drop_column('semester_enrollments', 'tournament_checked_in_at')
