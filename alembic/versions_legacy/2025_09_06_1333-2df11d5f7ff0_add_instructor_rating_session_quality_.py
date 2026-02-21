"""Add instructor_rating, session_quality, would_recommend to feedback

Revision ID: 2df11d5f7ff0
Revises: 3c8f68b69142
Create Date: 2025-09-06 13:33:47.233467

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates all base tables and columns. This migration was positioned before the
"initial_table_creation" migration but tried to modify tables/columns that are
now created in the root migration.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2df11d5f7ff0'
down_revision = '3c8f68b69142'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: Tables/columns already exist in root migration (w3mg03uvao74)
    pass


def downgrade() -> None:
    # NO-OP: Owned by root migration
    pass
