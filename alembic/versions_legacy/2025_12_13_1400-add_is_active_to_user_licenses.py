"""add_is_active_to_user_licenses

Revision ID: f1a2b3c4d5e6
Revises: 2d5e30afa335
Create Date: 2025-12-13 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '2d5e30afa335'
branch_labels = None
depends_on = None


def upgrade():
    """Add is_active column to user_licenses table."""
    # Add is_active column with default True
    op.add_column('user_licenses',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true',
                  comment='Whether this license is currently active (can be used for teaching/enrollment)')
    )


def downgrade():
    """Remove is_active column from user_licenses table."""
    op.drop_column('user_licenses', 'is_active')
