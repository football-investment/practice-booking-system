"""Add gamification tables for user achievements and stats

Revision ID: 41644b6e8548
Revises: 2df11d5f7ff0
Create Date: 2025-09-07 09:13:45.443671

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates all base tables and columns. This migration was positioned before the
"initial_table_creation" migration but tried to modify tables/columns that are
now created in the root migration.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '41644b6e8548'
down_revision = '2df11d5f7ff0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: Tables/columns already exist in root migration (w3mg03uvao74)
    pass


def downgrade() -> None:
    # NO-OP: Owned by root migration
    pass
