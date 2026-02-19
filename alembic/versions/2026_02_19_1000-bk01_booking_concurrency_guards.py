"""bk01: booking concurrency guards (uq_active_booking, uq_waitlist_position, uq_booking_attendance)

Revision ID: bk01concurr00
Revises: eb01concurr00
Create Date: 2026-02-19 10:00:00

Phase C DB-level guards for booking pipeline TOCTOU races:

  C-01  uq_active_booking — partial unique index on bookings(user_id, session_id)
        WHERE status != 'CANCELLED'.  Prevents duplicate active bookings (RACE-B01).

  C-02  uq_waitlist_position — partial unique index on bookings(session_id, waitlist_position)
        WHERE status = 'WAITLISTED'.  Prevents duplicate waitlist positions (RACE-B03).

  C-03  uq_booking_attendance — unique constraint on attendance(booking_id).
        Prevents duplicate attendance records per booking (RACE-B07).

These three constraints serve as the last-resort safety net even if the
application-layer FOR UPDATE locks are bypassed (e.g., through a direct DB
write or a bug in the lock acquisition).

Reference: docs/features/BOOKING_CONCURRENCY_AUDIT_2026-02-19.md
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "bk01concurr00"
down_revision = "eb01concurr00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # C-01: Prevent duplicate active bookings for same (user, session)
    # Partial: excludes CANCELLED rows so re-booking after cancellation is allowed.
    op.create_index(
        "uq_active_booking",
        "bookings",
        ["user_id", "session_id"],
        unique=True,
        postgresql_where=sa.text("status != 'CANCELLED'"),
    )

    # C-02: Prevent duplicate waitlist positions within same session
    # Partial: only applies to WAITLISTED rows.
    op.create_index(
        "uq_waitlist_position",
        "bookings",
        ["session_id", "waitlist_position"],
        unique=True,
        postgresql_where=sa.text("status = 'WAITLISTED'"),
    )

    # C-03: Each booking may have at most one attendance record
    op.create_unique_constraint(
        "uq_booking_attendance",
        "attendance",
        ["booking_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_booking_attendance", "attendance", type_="unique")
    op.drop_index("uq_waitlist_position", table_name="bookings")
    op.drop_index("uq_active_booking", table_name="bookings")
