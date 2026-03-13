"""add_skill_tier_reached_notification_type

Extend the notificationtype PostgreSQL enum with 'skill_tier_reached'
to support skill tier crossing notifications.

Revision ID: 2026_03_13_1400
Revises: 2026_03_12_1200
Create Date: 2026-03-13 14:00:00
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026_03_13_1400'
down_revision = '2026_03_12_1200'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL enum stores Python enum member NAMEs (uppercase), not values.
    # e.g. NotificationType.BOOKING_CONFIRMED → stored as 'BOOKING_CONFIRMED'
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'SKILL_TIER_REACHED'")


def downgrade():
    # PostgreSQL cannot remove enum values without recreation — leave as-is
    pass
