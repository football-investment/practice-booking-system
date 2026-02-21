"""add_unique_constraint_xp_transactions

Revision ID: 8e84e34793ac
Revises: 69606094ea87
Create Date: 2026-02-01 20:09:59.864294

IMPORTANT: This migration is now a NO-OP because the xp_transactions table
was never created in the migration chain (add_xp_system migration didn't run).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8e84e34793ac'
down_revision = '69606094ea87'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: xp_transactions table does not exist
    pass


def downgrade() -> None:
    # NO-OP
    pass