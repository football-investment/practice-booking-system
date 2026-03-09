"""add_attendance_partial_unique_null_booking

Revision ID: 2026_03_09_1400
Revises: 2026_03_02_2115
Create Date: 2026-03-09 14:00:00.000000

Closes the race-condition gap identified in the Sprint 53 DB constraint audit:

  Gap: Attendance table had no uniqueness constraint for tournament sessions
       (where booking_id IS NULL). Two concurrent mark_attendance calls for
       the same (user_id, session_id) pair could produce duplicate rows.

  Fix: Partial unique index covering the NULL-booking case only.
       Regular (non-tournament) sessions are already protected by:
         uq_booking_attendance UNIQUE (booking_id)
       because every regular attendance row has a non-NULL booking_id.

Index design:
  UNIQUE(user_id, session_id) WHERE booking_id IS NULL

  - Partial: only applies when booking_id IS NULL (tournament sessions)
  - Does NOT conflict with regular sessions (they have booking_id set)
  - Safe to apply: existing data has 0 rows with NULL booking_id and
    0 duplicate (user_id, session_id) pairs → no backfill needed

Note on quiz_attempts:
  The user suggested UNIQUE(session_id, user_id) WHERE completed_at IS NOT NULL
  on quiz_attempts. This table has no session_id column; the analogous constraint
  UNIQUE(user_id, quiz_id) WHERE completed_at IS NOT NULL would break the
  intentional multi-attempt design (users can retake quizzes). No pure-SQL
  unique constraint can prevent double-completion of the same attempt_id in
  a race — both concurrent readers see completed_at=NULL before either commits.
  The correct serialization is SELECT FOR UPDATE on the attempt fetch (applied
  in app/api/web_routes/quiz.py alongside this migration).
"""
from alembic import op
import sqlalchemy as sa


revision = '2026_03_09_1400'
down_revision = '2026_03_02_2115'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial unique index: only applies to tournament-session attendances
    # (booking_id IS NULL). Regular session attendances are already protected
    # by uq_booking_attendance UNIQUE(booking_id).
    op.create_index(
        'uq_attendance_user_session_no_booking',
        'attendance',
        ['user_id', 'session_id'],
        unique=True,
        postgresql_where=sa.text('booking_id IS NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_attendance_user_session_no_booking',
        table_name='attendance',
    )
