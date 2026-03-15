"""add performed_by_user_id to credit_transactions

Revision ID: 2026_03_13_1500
Revises: 2026_03_13_1400
Create Date: 2026-03-13 15:00:00.000000

Tracks which admin user performed a credit adjustment.
NULL for system-generated transactions (purchases, tournament rewards, etc.).
"""
from alembic import op
import sqlalchemy as sa

revision = '2026_03_13_1500'
down_revision = '2026_03_13_1400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'credit_transactions',
        sa.Column(
            'performed_by_user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
            comment='Admin user who performed this adjustment (NULL for system/user-initiated transactions)',
        )
    )
    op.create_index(
        'ix_credit_transactions_performed_by_user_id',
        'credit_transactions',
        ['performed_by_user_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_credit_transactions_performed_by_user_id', table_name='credit_transactions')
    op.drop_column('credit_transactions', 'performed_by_user_id')
