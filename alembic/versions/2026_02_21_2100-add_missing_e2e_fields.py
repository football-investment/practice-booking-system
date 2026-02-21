"""add missing e2e fields

Revision ID: 2026_02_21_2100
Revises: 1ec11c73ea62
Create Date: 2026-02-21 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_02_21_2100'
down_revision = '1ec11c73ea62'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing fields discovered during E2E test stabilization."""

    # semester_enrollments.tournament_checked_in_at
    # Pre-tournament check-in timestamp (player confirms attendance)
    op.execute("""
        ALTER TABLE semester_enrollments
        ADD COLUMN IF NOT EXISTS tournament_checked_in_at TIMESTAMP WITH TIME ZONE NULL
    """)

    # tournament_participations.skill_rating_delta
    # Skill rating change after tournament completion (JSONB: per-skill deltas)
    op.execute("""
        ALTER TABLE tournament_participations
        ADD COLUMN IF NOT EXISTS skill_rating_delta JSONB NULL
    """)

    # xp_transactions.idempotency_key
    # Prevent duplicate XP transactions (idempotency guarantee)
    op.execute("""
        ALTER TABLE xp_transactions
        ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(100) UNIQUE NULL
    """)

    # tournament_configurations.campus_schedule_overrides
    # Per-campus schedule overrides for multi-venue tournaments
    op.execute("""
        ALTER TABLE tournament_configurations
        ADD COLUMN IF NOT EXISTS campus_schedule_overrides JSONB NULL
    """)

    # sessions.campus_id
    # Campus/venue assignment for multi-campus tournaments
    op.execute("""
        ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS campus_id INTEGER NULL REFERENCES campuses(id)
    """)


def downgrade():
    """Remove fields added in this migration."""

    op.execute("ALTER TABLE semester_enrollments DROP COLUMN IF EXISTS tournament_checked_in_at")
    op.execute("ALTER TABLE tournament_participations DROP COLUMN IF EXISTS skill_rating_delta")
    op.execute("ALTER TABLE xp_transactions DROP COLUMN IF EXISTS idempotency_key")
    op.execute("ALTER TABLE tournament_configurations DROP COLUMN IF EXISTS campus_schedule_overrides")
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS campus_id")
