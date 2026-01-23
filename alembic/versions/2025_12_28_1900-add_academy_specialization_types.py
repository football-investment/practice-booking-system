"""add Academy Season specialization types to enum

Revision ID: add_academy_spec_types
Revises: add_location_type
Create Date: 2025-12-28 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_academy_spec_types'
down_revision = 'add_location_type'
branch_labels = None
depends_on = None


def upgrade():
    """Add LFA_PLAYER_PRE_ACADEMY and LFA_PLAYER_YOUTH_ACADEMY to specializationtype enum"""
    # Add new enum values using PostgreSQL ALTER TYPE
    # IF NOT EXISTS is available in PostgreSQL 9.1+
    op.execute("ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_PRE_ACADEMY'")
    op.execute("ALTER TYPE specializationtype ADD VALUE IF NOT EXISTS 'LFA_PLAYER_YOUTH_ACADEMY'")


def downgrade():
    """
    NOTE: PostgreSQL doesn't support removing enum values easily.
    This would require recreating the entire enum and updating all references.
    For safety, we leave the enum values in place.
    They won't cause issues if unused.
    """
    # Enum value removal is intentionally not implemented for safety
    # To fully remove, would need to:
    # 1. Create new enum without these values
    # 2. Update all columns using old enum to new enum
    # 3. Drop old enum
    # 4. Rename new enum to old name
    # This is risky and rarely needed, so we leave values in place
    pass
