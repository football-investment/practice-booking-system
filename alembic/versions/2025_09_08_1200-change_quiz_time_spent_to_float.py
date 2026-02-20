"""Change quiz time_spent_minutes to float

Revision ID: change_quiz_time_spent_to_float
Revises: 52d803f6d8dc
Create Date: 2025-09-08 12:00:00.000000

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates all base tables and columns. This migration was positioned before the
"initial_table_creation" migration but tried to modify tables/columns that are
now created in the root migration.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_quiz_time_spent_to_float'
down_revision = '52d803f6d8dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: Tables/columns already exist in root migration (w3mg03uvao74)
    pass


def downgrade() -> None:
    # NO-OP: Owned by root migration
    pass
