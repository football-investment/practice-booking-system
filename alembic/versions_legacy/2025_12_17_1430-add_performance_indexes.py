"""add performance indexes

Revision ID: a9b8c7d6e5f4
Revises: 4f8c9d2e6a1b
Create Date: 2025-12-17 14:30:00.000000

IMPORTANT: This migration adds 4 critical indexes identified in the database audit.
These indexes significantly improve query performance for:
- Punctuality calculations (attendance.check_in_time)
- Achievement timelines (user_achievements.earned_at)
- Transaction history (credit_transactions.created_at)
- Booking history (bookings.created_at)

Database Quality Impact: 90.75% → 92%+ (estimated)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9b8c7d6e5f4'
down_revision = '4f8c9d2e6a1b'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add 4 performance-critical indexes identified in database audit.

    These indexes improve performance for:
    1. Punctuality score calculations
    2. Achievement timeline queries
    3. Credit transaction history
    4. Booking history queries
    """

    # Index 1: attendance.check_in_time
    # Used in: Punctuality calculations, late check-in detection
    # Impact: HIGH - Improves UserStats.punctuality_score calculation
    op.create_index(
        'idx_attendance_check_in_time',
        'attendance',
        ['check_in_time'],
        unique=False
    )

    # Index 2: user_achievements.earned_at
    # Used in: Achievement timeline, recent achievements, badge display
    # Impact: MEDIUM - Improves achievement timeline queries
    op.create_index(
        'idx_user_achievements_earned_at',
        'user_achievements',
        ['earned_at'],
        unique=False
    )

    # Index 3: credit_transactions.created_at
    # Used in: Transaction history, credit audit trail, date range queries
    # Impact: MEDIUM-HIGH - Improves credit transaction history
    op.create_index(
        'idx_credit_transactions_created_at',
        'credit_transactions',
        ['created_at'],
        unique=False
    )

    # Index 4: bookings.created_at
    # Used in: Booking history, recent bookings, date range queries
    # Impact: MEDIUM - Improves booking history queries
    op.create_index(
        'idx_bookings_created_at',
        'bookings',
        ['created_at'],
        unique=False
    )

    print("✅ Added 4 performance indexes:")
    print("   - idx_attendance_check_in_time")
    print("   - idx_user_achievements_earned_at")
    print("   - idx_credit_transactions_created_at")
    print("   - idx_bookings_created_at")


def downgrade():
    """
    Remove the 4 performance indexes.

    WARNING: This will degrade query performance for:
    - Punctuality calculations
    - Achievement timelines
    - Credit transaction history
    - Booking history
    """

    # Remove indexes in reverse order
    op.drop_index('idx_bookings_created_at', table_name='bookings')
    op.drop_index('idx_credit_transactions_created_at', table_name='credit_transactions')
    op.drop_index('idx_user_achievements_earned_at', table_name='user_achievements')
    op.drop_index('idx_attendance_check_in_time', table_name='attendance')

    print("⚠️ Removed 4 performance indexes (performance may degrade)")
