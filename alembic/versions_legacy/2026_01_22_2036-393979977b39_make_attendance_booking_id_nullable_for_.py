"""make_attendance_booking_id_nullable_for_tournaments

Revision ID: 393979977b39
Revises: 5bec2bb404df
Create Date: 2026-01-22 20:36:54.185739

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '393979977b39'
down_revision = '5bec2bb404df'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Make attendance.booking_id nullable to support tournament sessions without bookings.

    Tournament sessions use:
    - semester_enrollments (tournament enrollment)
    - participant_user_ids (explicit match participants)

    Attendance records for tournament sessions will have:
    - user_id + session_id (match participant)
    - booking_id = NULL (no booking required)
    """
    # Make booking_id nullable
    op.alter_column('attendance', 'booking_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    """Revert booking_id to non-nullable"""
    # Note: This will fail if there are attendance records with NULL booking_id
    op.alter_column('attendance', 'booking_id',
                    existing_type=sa.Integer(),
                    nullable=False)