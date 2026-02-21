"""Initial table creation

Revision ID: a5ce34a0b659
Revises: a50b55dcf030
Create Date: 2025-09-16 10:01:33.238222

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates all these base tables. This migration was previously positioned incorrectly
as the 15th migration in the chain, but it created foundational tables that earlier
migrations tried to modify. The fix was to move all table creation to the root.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5ce34a0b659'
down_revision = 'a50b55dcf030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: All base tables are now created in the root migration (w3mg03uvao74)
    # This migration was previously positioned incorrectly (15th instead of 1st).
    # Tables already exist from root migration, so we skip creation here.
    pass


def downgrade() -> None:
    # NO-OP: All tables are owned by root migration
    # Downgrade is not supported below root migration.
    pass
