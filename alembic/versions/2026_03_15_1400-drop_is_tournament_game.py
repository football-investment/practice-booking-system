"""drop is_tournament_game column from sessions

Revision ID: 2026_03_15_1400
Revises: 2026_03_15_1300
Create Date: 2026-03-15 14:00:00.000000

M-10: Removes the legacy is_tournament_game boolean column now that event_category
      has been backfilled (M-08/M-09) and the hybrid_property handles all reads/writes.

Pre-conditions verified before this migration:
  - All rows have event_category set (770 TRAINING, 3362 MATCH, 0 NULL)
  - All filter queries in service layer use event_category (via hybrid_property)
  - Session model has hybrid_property is_tournament_game → event_category bridge
"""
from alembic import op

revision = '2026_03_15_1400'
down_revision = '2026_03_15_1300'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('ix_sessions_is_tournament_game', table_name='sessions', if_exists=True)
    op.drop_column('sessions', 'is_tournament_game')


def downgrade() -> None:
    import sqlalchemy as sa
    op.add_column(
        'sessions',
        sa.Column(
            'is_tournament_game',
            sa.Boolean(),
            nullable=True,
            comment='LEGACY — use event_category instead',
        )
    )
    op.create_index('ix_sessions_is_tournament_game', 'sessions', ['is_tournament_game'])
    # Restore from event_category (best-effort reverse).
    # COALESCE handles rows with NULL event_category (created during rollback chain)
    # — they get FALSE rather than NULL, satisfying the NOT NULL constraint.
    op.execute(
        "UPDATE sessions SET is_tournament_game = COALESCE(event_category = 'MATCH', FALSE)"
    )
    op.execute("ALTER TABLE sessions ALTER COLUMN is_tournament_game SET NOT NULL")
    op.execute("ALTER TABLE sessions ALTER COLUMN is_tournament_game SET DEFAULT FALSE")
