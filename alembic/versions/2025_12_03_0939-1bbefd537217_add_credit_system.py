"""add_credit_system

Revision ID: 1bbefd537217
Revises: ec7db8d19614
Create Date: 2025-12-03 09:39:15.844296

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1bbefd537217'
down_revision = 'ec7db8d19614'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add credit fields to user_licenses table
    op.add_column('user_licenses', sa.Column('credit_balance', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user_licenses', sa.Column('credit_purchased', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('user_licenses', sa.Column('credit_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Add enrollment_cost to semesters table
    op.add_column('semesters', sa.Column('enrollment_cost', sa.Integer(), nullable=False, server_default='500'))

    # Create credit_transactions table
    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_license_id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('semester_id', sa.Integer(), nullable=True),
        sa.Column('enrollment_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_license_id'], ['user_licenses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['enrollment_id'], ['semester_enrollments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_credit_transactions_user_license_id', 'credit_transactions', ['user_license_id'])
    op.create_index('ix_credit_transactions_created_at', 'credit_transactions', ['created_at'])


def downgrade() -> None:
    # Drop credit_transactions table
    op.drop_index('ix_credit_transactions_created_at')
    op.drop_index('ix_credit_transactions_user_license_id')
    op.drop_table('credit_transactions')

    # Remove enrollment_cost from semesters
    op.drop_column('semesters', 'enrollment_cost')

    # Remove credit fields from user_licenses
    op.drop_column('user_licenses', 'credit_expires_at')
    op.drop_column('user_licenses', 'credit_purchased')
    op.drop_column('user_licenses', 'credit_balance')