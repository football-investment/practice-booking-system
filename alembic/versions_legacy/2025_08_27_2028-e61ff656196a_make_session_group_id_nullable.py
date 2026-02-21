"""Make session group_id nullable

Revision ID: e61ff656196a
Revises: w3mg03uvao74
Create Date: 2025-08-27 20:28:35.777385

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates the sessions table with group_id already nullable from the start.

Previously this was the root migration (down_revision = None), but that caused
the migration chain to be corrupted - it tried to ALTER a table that didn't exist yet.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e61ff656196a'
down_revision = 'w3mg03uvao74'  # Now revises the true root migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NO-OP: sessions.group_id is already nullable in the root migration
    # The root migration (w3mg03uvao74) creates sessions table with group_id nullable.
    # This migration is kept for backward compatibility with existing databases.
    pass


def downgrade() -> None:
    # NO-OP: cannot downgrade past root migration
    pass