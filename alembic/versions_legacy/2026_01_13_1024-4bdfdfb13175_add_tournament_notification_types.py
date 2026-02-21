"""add_tournament_notification_types

Revision ID: 4bdfdfb13175
Revises: 71f227317750
Create Date: 2026-01-13 10:24:58.662225

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4bdfdfb13175'
down_revision = '71f227317750'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new notification types for tournament workflow
    op.execute("""
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'TOURNAMENT_APPLICATION_APPROVED';
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'TOURNAMENT_APPLICATION_REJECTED';
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'TOURNAMENT_DIRECT_INVITATION';
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'TOURNAMENT_INSTRUCTOR_ACCEPTED';
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'TOURNAMENT_INSTRUCTOR_DECLINED';
    """)


def downgrade() -> None:
    # Note: PostgreSQL does not support removing enum values directly
    # You would need to recreate the enum type without these values
    # For now, we'll leave this as a no-op since removing enum values is complex
    pass