"""add_payment_reference_to_user_license

Revision ID: 9eb7a371b55c
Revises: ae86a0a12e8e
Create Date: 2025-11-29 20:53:51.962145

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9eb7a371b55c'
down_revision = 'ae86a0a12e8e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add payment_reference_code column to user_licenses table
    op.add_column('user_licenses',
                  sa.Column('payment_reference_code', sa.String(length=50), nullable=True))

    # Add unique constraint and index
    op.create_index(op.f('ix_user_licenses_payment_reference_code'),
                    'user_licenses', ['payment_reference_code'], unique=True)


def downgrade() -> None:
    # Remove index and column
    op.drop_index(op.f('ix_user_licenses_payment_reference_code'),
                  table_name='user_licenses')
    op.drop_column('user_licenses', 'payment_reference_code')