"""add_credit_payment_reference_to_user

Revision ID: a3fb1e8db7c8
Revises: e0b638299ddb
Create Date: 2025-12-03 15:02:56.062248

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3fb1e8db7c8'
down_revision = 'e0b638299ddb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add credit_payment_reference field to users table
    op.add_column('users', sa.Column('credit_payment_reference', sa.String(length=50), nullable=True, comment='Unique payment reference code for credit purchases (közlemény)'))
    op.create_unique_constraint('uq_users_credit_payment_reference', 'users', ['credit_payment_reference'])

    # Generate payment reference codes for existing users with credit_purchased > 0
    # Format: CREDIT-YYYY-UUUUU-RRRR (e.g., CREDIT-2025-00002-A5F3)
    op.execute("""
        UPDATE users
        SET credit_payment_reference = CONCAT(
            'CREDIT-',
            '2025-',
            LPAD(id::text, 5, '0'),
            '-',
            UPPER(SUBSTRING(MD5(CONCAT('credit', id::text, email)) FROM 1 FOR 4))
        )
        WHERE credit_payment_reference IS NULL;
    """)


def downgrade() -> None:
    # Drop unique constraint and column
    op.drop_constraint('uq_users_credit_payment_reference', 'users', type_='unique')
    op.drop_column('users', 'credit_payment_reference')