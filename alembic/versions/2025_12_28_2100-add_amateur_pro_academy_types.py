"""Add AMATEUR and PRO Academy Season types to SpecializationType enum

Revision ID: add_amateur_pro_academy_types
Revises: 03be2a3405e3
Create Date: 2025-12-28 21:00:00.000000

This migration adds two new Academy Season types for AMATEUR and PRO age groups:
- LFA_PLAYER_AMATEUR_ACADEMY: Full year academy for AMATEUR (14+ years)
- LFA_PLAYER_PRO_ACADEMY: Full year academy for PRO (14+ years)

This completes the consistent PARTNER/CENTER location distinction for all 4 age groups:
- PRE (5-13): Mini Season (monthly) + Academy Season (CENTER only)
- YOUTH (14-18): Mini Season (quarterly) + Academy Season (CENTER only)
- AMATEUR (14+): Mini Season (quarterly) + Academy Season (CENTER only)
- PRO (14+): Mini Season (quarterly) + Academy Season (CENTER only)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_amateur_pro_academy_types'
down_revision = '03be2a3405e3'
branch_labels = None
depends_on = None


def upgrade():
    """Add AMATEUR and PRO Academy Season enum values"""
    # Add new enum values to SpecializationType
    # Using IF NOT EXISTS pattern for idempotent migrations
    op.execute(
        "ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_AMATEUR_ACADEMY'"
    )
    op.execute(
        "ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_PRO_ACADEMY'"
    )


def downgrade():
    """
    PostgreSQL does not support removing enum values easily.
    To downgrade, you would need to:
    1. Remove all references to these enum values in the database
    2. Create a new enum type without these values
    3. Alter columns to use the new enum type
    4. Drop the old enum type

    This is not implemented as it's rarely needed in production.
    """
    pass
