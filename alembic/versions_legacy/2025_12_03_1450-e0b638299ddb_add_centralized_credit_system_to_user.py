"""add_centralized_credit_system_to_user

Revision ID: e0b638299ddb
Revises: 1bbefd537217
Create Date: 2025-12-03 14:50:53.942025

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0b638299ddb'
down_revision = '1bbefd537217'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add centralized credit fields to users table
    op.add_column('users', sa.Column('credit_balance', sa.Integer(), nullable=False, server_default='0', comment='Current available credits (can be used across all specializations)'))
    op.add_column('users', sa.Column('credit_purchased', sa.Integer(), nullable=False, server_default='0', comment='Total credits purchased by this user (for transaction history)'))

    # Migrate existing credits from user_licenses to users
    # Sum up all credit_balance and credit_purchased from all licenses per user
    op.execute("""
        UPDATE users
        SET
            credit_balance = COALESCE((
                SELECT SUM(ul.credit_balance)
                FROM user_licenses ul
                WHERE ul.user_id = users.id
            ), 0),
            credit_purchased = COALESCE((
                SELECT SUM(ul.credit_purchased)
                FROM user_licenses ul
                WHERE ul.user_id = users.id
            ), 0)
    """)


def downgrade() -> None:
    # Remove centralized credit fields from users table
    op.drop_column('users', 'credit_purchased')
    op.drop_column('users', 'credit_balance')