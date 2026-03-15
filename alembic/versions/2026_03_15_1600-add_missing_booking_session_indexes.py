"""add missing indexes on bookings and sessions for query performance

Revision ID: 2026_03_15_1600
Revises: 2026_03_15_1500
Create Date: 2026-03-15 16:00:00.000000

Adds indexes for the most frequently-executed queries:

bookings table
--------------
  ix_bookings_session_status  (session_id, status)  — composite
      Used by every booking creation:
        SELECT COUNT(*) FROM bookings WHERE session_id=? AND status='CONFIRMED'
        SELECT COUNT(*) FROM bookings WHERE session_id=? AND status='WAITLISTED'
      Without this index, each booking request table-scans bookings.

  ix_bookings_user_id  (user_id)
      Used by duplicate-booking check:
        SELECT * FROM bookings WHERE user_id=? AND session_id=? AND status!='CANCELLED'
      Also used for "a student's booking history" queries.

  ix_bookings_session_id  (session_id)
      Single-column companion to ix_bookings_session_status for full-session
      lookups (e.g. admin booking list, attendance, waitlist management).

sessions table
--------------
  ix_sessions_semester_id  (semester_id)
      Used by every page that lists sessions in a semester:
        SELECT * FROM sessions WHERE semester_id=?
      Without this index, every semester page table-scans all sessions.

  ix_sessions_date_start  (date_start)
      Used for upcoming-session ranges:
        SELECT * FROM sessions WHERE date_start BETWEEN ? AND ?
      Supports calendar views and schedule queries.
"""
from alembic import op

revision = '2026_03_15_1600'
down_revision = '2026_03_15_1500'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bookings: composite index for capacity-check hot path
    op.create_index(
        "ix_bookings_session_status",
        "bookings",
        ["session_id", "status"],
    )
    # bookings: user lookup (booking history, duplicate-check)
    op.create_index(
        "ix_bookings_user_id",
        "bookings",
        ["user_id"],
    )
    # bookings: single-column session lookup (admin views, attendance)
    op.create_index(
        "ix_bookings_session_id",
        "bookings",
        ["session_id"],
    )
    # sessions: semester listing (most common sessions query)
    op.create_index(
        "ix_sessions_semester_id",
        "sessions",
        ["semester_id"],
    )
    # sessions: date-range scheduling queries
    op.create_index(
        "ix_sessions_date_start",
        "sessions",
        ["date_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_date_start", table_name="sessions")
    op.drop_index("ix_sessions_semester_id", table_name="sessions")
    op.drop_index("ix_bookings_session_id", table_name="bookings")
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_index("ix_bookings_session_status", table_name="bookings")
