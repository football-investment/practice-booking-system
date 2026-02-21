"""Add nickname field to User model

Revision ID: a7ce0b5b014b
Revises: 3e6ac10683c0
Create Date: 2025-09-10 19:53:14.671373

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates all base tables and columns. This migration was positioned before the
"initial_table_creation" migration but tried to modify tables/columns that are
now created in the root migration.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7ce0b5b014b'
down_revision = '3e6ac10683c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: Tables/columns already exist in root migration (w3mg03uvao74)
    pass


def downgrade() -> None:
    # NO-OP: Owned by root migration
    pass
