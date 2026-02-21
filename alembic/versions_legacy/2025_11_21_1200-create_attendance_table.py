"""create attendance table

Revision ID: a1b2c3d4e5f6
Revises: f00c64f4c615
Create Date: 2025-11-21 12:00:00.000000

IMPORTANT: This migration is now a NO-OP because the root migration (w3mg03uvao74)
creates the attendance table already.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f00c64f4c615'
branch_labels = None
depends_on = None


def upgrade():
    # NO-OP: attendance table already exists in root migration (w3mg03uvao74)
    pass


def downgrade():
    # NO-OP: table is owned by root migration
    pass
