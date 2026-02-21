"""add_user_id_to_credit_transactions

Revision ID: 7cba9938911d
Revises: e48f7d0e7b43
Create Date: 2026-01-04 11:03:21.765952

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7cba9938911d'
down_revision = 'e48f7d0e7b43'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column (nullable for now, will populate)
    op.add_column('credit_transactions', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_credit_transactions_user_id'), 'credit_transactions', ['user_id'], unique=False)
    op.create_foreign_key('fk_credit_transactions_user_id', 'credit_transactions', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # Make user_license_id nullable
    op.alter_column('credit_transactions', 'user_license_id',
                    existing_type=sa.Integer(),
                    nullable=True)

    # Add check constraint ensuring exactly one of user_id or user_license_id is set
    op.create_check_constraint(
        'check_one_credit_reference',
        'credit_transactions',
        '(user_id IS NOT NULL AND user_license_id IS NULL) OR (user_id IS NULL AND user_license_id IS NOT NULL)'
    )


def downgrade() -> None:
    # Remove check constraint
    op.drop_constraint('check_one_credit_reference', 'credit_transactions', type_='check')

    # Make user_license_id required again
    op.alter_column('credit_transactions', 'user_license_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # Remove user_id column and related constraints
    op.drop_constraint('fk_credit_transactions_user_id', 'credit_transactions', type_='foreignkey')
    op.drop_index(op.f('ix_credit_transactions_user_id'), table_name='credit_transactions')
    op.drop_column('credit_transactions', 'user_id')