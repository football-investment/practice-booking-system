"""Add attended_status column to bookings table

Revision ID: 3c8f68b69142
Revises: e61ff656196a
Create Date: 2025-09-03 04:08:30.283316

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates the bookings table with attended_status column already included.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c8f68b69142'
down_revision = 'e61ff656196a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: bookings.attended_status is already present in the root migration
    pass


def downgrade() -> None:
    # NO-OP: column is owned by root migration
    pass
