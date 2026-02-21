"""add_license_expiration_fields

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2025-12-13 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g2h3i4j5k6l7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    """Add license expiration and renewal tracking fields."""
    # Add expires_at (nullable - null = no expiration yet)
    op.add_column('user_licenses',
        sa.Column('expires_at', sa.DateTime(), nullable=True,
                  comment='License expiration date (null = no expiration yet, perpetual until first renewal)')
    )

    # Add last_renewed_at (nullable - null = never renewed)
    op.add_column('user_licenses',
        sa.Column('last_renewed_at', sa.DateTime(), nullable=True,
                  comment='When license was last renewed')
    )

    # Add renewal_cost (default 1000 credits)
    op.add_column('user_licenses',
        sa.Column('renewal_cost', sa.Integer(), nullable=False, server_default='1000',
                  comment='Credit cost to renew this license (default: 1000 credits)')
    )


def downgrade():
    """Remove license expiration and renewal fields."""
    op.drop_column('user_licenses', 'renewal_cost')
    op.drop_column('user_licenses', 'last_renewed_at')
    op.drop_column('user_licenses', 'expires_at')
