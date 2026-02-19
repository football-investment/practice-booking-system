"""rw01: reward/XP pipeline concurrency guards

Revision ID: rw01concurr00
Revises: bk01concurr00
Create Date: 2026-02-19 12:00:00.000000

Closes RACE-R05 and RACE-R06 from REWARD_XP_CONCURRENCY_AUDIT_2026-02-19.md.

Application-layer fixes (FOR UPDATE, SAVEPOINT, atomic SQL UPDATE) are in:
  - app/services/tournament/results/finalization/tournament_finalizer.py   (R01/R03)
  - app/services/tournament/tournament_reward_orchestrator.py               (R02/R04)
  - app/services/tournament/tournament_badge_service.py                    (R05)
  - app/services/tournament/tournament_participation_service.py             (R06/R07)
  - app/models/xp_transaction.py                                           (R06 column)

DB changes in this migration:
  C-R01: uq_user_tournament_badge — prevents duplicate badge awards per type per tournament
  C-R02: uq_xp_transaction_reward — prevents duplicate XP grants via idempotency_key
  C-R03: Add idempotency_key column to xp_transactions
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'rw01concurr00'
down_revision = 'bk01concurr00'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── C-R03: Add idempotency_key column to xp_transactions ─────────────────
    # Nullable: existing rows have no key; new reward rows will have one set.
    op.add_column(
        'xp_transactions',
        sa.Column('idempotency_key', sa.String(255), nullable=True)
    )

    # Index on idempotency_key for lookup speed (non-unique; partial unique below)
    op.create_index(
        'ix_xp_transactions_idempotency_key',
        'xp_transactions',
        ['idempotency_key'],
        unique=False,
    )

    # ── C-R02: Unique partial index on xp_transactions idempotency_key ───────
    # Prevents duplicate XP transactions when reward distribution is retried.
    # Partial: only enforced where idempotency_key IS NOT NULL (legacy rows exempt).
    op.execute("""
        CREATE UNIQUE INDEX uq_xp_transaction_idempotency
          ON xp_transactions (idempotency_key)
          WHERE idempotency_key IS NOT NULL
    """)

    # ── C-R01: Unique index on tournament_badges (user_id, semester_id, badge_type) ──
    # Prevents duplicate badge rows from concurrent award_badge() calls.
    op.execute("""
        CREATE UNIQUE INDEX uq_user_tournament_badge
          ON tournament_badges (user_id, semester_id, badge_type)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_user_tournament_badge")
    op.execute("DROP INDEX IF EXISTS uq_xp_transaction_idempotency")
    op.drop_index('ix_xp_transactions_idempotency_key', table_name='xp_transactions')
    op.drop_column('xp_transactions', 'idempotency_key')
