"""add_xp_system

Revision ID: add_xp_system_001
Revises: f7592a774d52
Create Date: 2026-01-21 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_xp_system_001'
down_revision = 'f7592a774d52'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add xp_balance column to users table
    op.add_column('users', sa.Column('xp_balance', sa.Integer(), nullable=False, server_default='0'))

    # Create xp_transactions table
    op.create_table(
        'xp_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('semester_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_xp_transactions_id', 'xp_transactions', ['id'], unique=False)
    op.create_index('ix_xp_transactions_user_id', 'xp_transactions', ['user_id'], unique=False)
    op.create_index('ix_xp_transactions_created_at', 'xp_transactions', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_xp_transactions_created_at', table_name='xp_transactions')
    op.drop_index('ix_xp_transactions_user_id', table_name='xp_transactions')
    op.drop_index('ix_xp_transactions_id', table_name='xp_transactions')

    # Drop xp_transactions table
    op.drop_table('xp_transactions')

    # Remove xp_balance column from users
    op.drop_column('users', 'xp_balance')
