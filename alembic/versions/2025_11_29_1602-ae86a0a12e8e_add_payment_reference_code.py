"""add_payment_reference_code

Revision ID: ae86a0a12e8e
Revises: 656cf0b3dd6e
Create Date: 2025-11-29 16:02:27.294573

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae86a0a12e8e'
down_revision = '656cf0b3dd6e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add payment_reference_code column to semester_enrollments table
    op.add_column('semester_enrollments',
                  sa.Column('payment_reference_code', sa.String(length=50), nullable=True))

    # Add unique constraint and index
    op.create_index(op.f('ix_semester_enrollments_payment_reference_code'),
                    'semester_enrollments', ['payment_reference_code'], unique=True)


def downgrade() -> None:
    # Remove index and column
    op.drop_index(op.f('ix_semester_enrollments_payment_reference_code'),
                  table_name='semester_enrollments')
    op.drop_column('semester_enrollments', 'payment_reference_code')