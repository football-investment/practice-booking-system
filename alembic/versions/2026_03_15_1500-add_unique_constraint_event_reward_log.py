"""add unique constraint to event_reward_logs (user_id, session_id)

Revision ID: 2026_03_15_1500
Revises: 2026_03_15_1400
Create Date: 2026-03-15 15:00:00.000000

Ensures that award_session_completion() is safe under concurrent execution.
Without this constraint, concurrent INSERT calls for the same (user, session)
pair could produce duplicate rows due to a TOCTOU race in the Python-level
read-modify-write upsert logic.

The reward service now uses PostgreSQL INSERT … ON CONFLICT DO UPDATE, which
is atomic and eliminates the race entirely. This constraint acts as a
database-level safety net.

The upgrade step first removes any pre-existing duplicate rows (keeping the
latest id for each pair) so the constraint creation never fails on databases
that already have data.
"""
from alembic import op

revision = '2026_03_15_1500'
down_revision = '2026_03_15_1400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove pre-existing duplicate (user_id, session_id) pairs — keep MAX(id)
    op.execute("""
        DELETE FROM event_reward_logs
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM event_reward_logs
            GROUP BY user_id, session_id
        )
    """)
    op.create_unique_constraint(
        "uq_event_reward_log_user_session",
        "event_reward_logs",
        ["user_id", "session_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_event_reward_log_user_session",
        "event_reward_logs",
        type_="unique",
    )
