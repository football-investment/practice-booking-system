"""p2_separate_tournament_config_to_own_table

Revision ID: cc889842cb21
Revises: 82956292b4e4
Create Date: 2026-01-29 16:00:00.000000

IMPORTANT: This migration is now a NO-OP.
Original goal was to separate tournament configuration to own table, but this requires
complex data migration from semesters table columns that may not exist in all environments.
Converted to NO-OP for migration chain stability.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cc889842cb21'
down_revision = '82956292b4e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: Complex data migration skipped for stability
    pass


def downgrade() -> None:
    # NO-OP
    pass
