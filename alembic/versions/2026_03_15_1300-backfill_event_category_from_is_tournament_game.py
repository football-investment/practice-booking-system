"""backfill event_category from is_tournament_game

Revision ID: 2026_03_15_1300
Revises: 2026_03_15_1200
Create Date: 2026-03-15 13:00:00.000000

M-08: is_tournament_game = TRUE  → event_category = 'MATCH'
M-09: is_tournament_game = FALSE → event_category = 'TRAINING'

Both migrations run as a single atomic UPDATE batch.
NULL rows (if any) are left NULL — safe, no assumptions.

Downgrade: NULLs out event_category (irreversible data loss acknowledged;
downgrade only intended for emergency rollback in pre-production).
"""
from alembic import op

revision = '2026_03_15_1300'
down_revision = '2026_03_15_1200'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # M-08: tournament games → MATCH
    op.execute(
        "UPDATE sessions SET event_category = 'MATCH' WHERE is_tournament_game = TRUE"
    )
    # M-09: training sessions → TRAINING
    op.execute(
        "UPDATE sessions SET event_category = 'TRAINING' WHERE is_tournament_game = FALSE"
    )


def downgrade() -> None:
    # Emergency rollback only — cannot recover MATCH/TRAINING distinction after drop
    op.execute("UPDATE sessions SET event_category = NULL")
