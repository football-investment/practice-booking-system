"""Add checkin_opens_at to semesters; make tournament_status_history.changed_by nullable

Revision ID: 2026_03_27_1000
Revises: 2026_03_26_1500
Create Date: 2026-03-27 10:00:00.000000

Changes:
1. semesters.checkin_opens_at TIMESTAMPTZ NULL
   - Stores the UTC datetime when check-in auto-opens for a tournament.
   - NULL = manual-only (admin must press "Open Check-In" button).
   - APScheduler polls every minute and auto-transitions
     ENROLLMENT_CLOSED → CHECK_IN_OPEN when checkin_opens_at <= NOW().

2. tournament_status_history.changed_by: INTEGER NOT NULL → NULLABLE
   - Allows system/scheduler-initiated status changes (changed_by = NULL).
   - Human-initiated changes still set changed_by to the acting user's id.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '2026_03_27_1000'
down_revision = '2026_03_26_1500'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add checkin_opens_at to semesters
    op.add_column(
        'semesters',
        sa.Column(
            'checkin_opens_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment="UTC datetime when check-in auto-opens (NULL = manual only)"
        )
    )

    # 2. Make changed_by nullable so scheduler can record system-initiated transitions
    op.alter_column(
        'tournament_status_history',
        'changed_by',
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade():
    # Restore NOT NULL on changed_by (rows with NULL will cause failure — clean them first)
    op.execute(
        "DELETE FROM tournament_status_history WHERE changed_by IS NULL"
    )
    op.alter_column(
        'tournament_status_history',
        'changed_by',
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_column('semesters', 'checkin_opens_at')
