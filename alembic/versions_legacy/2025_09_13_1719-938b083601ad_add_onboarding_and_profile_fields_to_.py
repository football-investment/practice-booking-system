"""Add onboarding and profile fields to User model

Revision ID: 938b083601ad
Revises: ab3db1e041b8
Create Date: 2025-09-13 17:19:31.394780

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates all base tables and columns. This migration was positioned before the
"initial_table_creation" migration but tried to modify tables/columns that are
now created in the root migration.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '938b083601ad'
down_revision = 'ab3db1e041b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: Tables/columns already exist in root migration (w3mg03uvao74)
    pass


def downgrade() -> None:
    # NO-OP: Owned by root migration
    pass
