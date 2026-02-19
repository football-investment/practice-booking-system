"""add_notifications_table

Revision ID: d64255498079
Revises: 884089caac2f
Create Date: 2025-12-30 18:36:38.045393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd64255498079'
down_revision = '884089caac2f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend existing notifications table with new fields for instructor job offers

    # Add new notification types to the enum
    op.execute("""
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'job_offer';
    """)
    op.execute("""
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'offer_accepted';
    """)
    op.execute("""
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'offer_declined';
    """)

    # Add new columns
    op.add_column('notifications', sa.Column('link', sa.String(length=255), nullable=True))
    op.add_column('notifications', sa.Column('related_semester_id', sa.Integer(), nullable=True))
    op.add_column('notifications', sa.Column('related_request_id', sa.Integer(), nullable=True))

    # Add foreign key constraints
    op.create_foreign_key(
        'notifications_related_semester_id_fkey',
        'notifications', 'semesters',
        ['related_semester_id'], ['id']
    )
    op.create_foreign_key(
        'notifications_related_request_id_fkey',
        'notifications', 'instructor_assignment_requests',
        ['related_request_id'], ['id']
    )


def downgrade() -> None:
    # Drop foreign key constraints
    op.drop_constraint('notifications_related_request_id_fkey', 'notifications', type_='foreignkey')
    op.drop_constraint('notifications_related_semester_id_fkey', 'notifications', type_='foreignkey')

    # Drop columns
    op.drop_column('notifications', 'related_request_id')
    op.drop_column('notifications', 'related_semester_id')
    op.drop_column('notifications', 'link')

    # Note: Cannot remove enum values in PostgreSQL, they remain but unused