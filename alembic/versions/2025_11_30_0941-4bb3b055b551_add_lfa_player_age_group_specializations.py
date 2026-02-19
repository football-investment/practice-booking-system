"""add_lfa_player_age_group_specializations

Revision ID: 4bb3b055b551
Revises: 9a5fec2c6a94
Create Date: 2025-11-30 09:41:59.544899

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4bb3b055b551'
down_revision = '9a5fec2c6a94'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new LFA Player age group specializations to specializationtype enum
    op.execute("ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_PRE'")
    op.execute("ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_YOUTH'")
    op.execute("ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_AMATEUR'")
    op.execute("ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_PRO'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly
    # You would need to recreate the enum type without these values
    # This is a destructive operation, so we'll leave it as a no-op
    pass