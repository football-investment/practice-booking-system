"""add_payment_verified_to_user_license

Revision ID: 9a5fec2c6a94
Revises: 9eb7a371b55c
Create Date: 2025-11-30 09:11:07.602114

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a5fec2c6a94'
down_revision = '9eb7a371b55c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add payment_verified and payment_verified_at columns to user_licenses table
    op.add_column('user_licenses',
                  sa.Column('payment_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('user_licenses',
                  sa.Column('payment_verified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove payment_verified and payment_verified_at columns
    op.drop_column('user_licenses', 'payment_verified_at')
    op.drop_column('user_licenses', 'payment_verified')