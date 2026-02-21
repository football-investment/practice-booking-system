"""add_tournament_status_history_table

Revision ID: f7592a774d52
Revises: f222a15fc815
Create Date: 2026-01-15 09:10:07.876974

IMPORTANT: This migration is now a NO-OP because the tournament_status_history table
was already created in migration 71aab5034cd9 (add_tournament_status_enum_and_history).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f7592a774d52'
down_revision = 'f222a15fc815'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: tournament_status_history table already exists (created in 71aab5034cd9)
    pass


def downgrade() -> None:
    # NO-OP: table is owned by migration 71aab5034cd9
    pass