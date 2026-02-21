"""add_idempotency_key_credit_transactions

Revision ID: 2c77e5ab056f
Revises: d73137711dd5
Create Date: 2026-02-01 20:13:17.720848

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c77e5ab056f'
down_revision = 'd73137711dd5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add idempotency_key column to credit_transactions table.

    Prevents DUAL PATH bug where multiple services (RewardDistributor,
    CreditService, EnrollmentService) create duplicate credit transactions
    for the same logical operation.

    Business Invariant: One credit transaction per idempotency_key.
    Example: "tournament_123_reward_user_5" can only create ONE transaction.

    The idempotency_key format should be: "{source_type}_{source_id}_{user_id}_{operation}"
    Examples:
    - "tournament_123_reward_5"
    - "enrollment_456_refund_7"
    - "session_789_attendance_bonus_3"
    """
    # Step 1: Add nullable idempotency_key column
    op.add_column(
        'credit_transactions',
        sa.Column('idempotency_key', sa.String(255), nullable=True)
    )

    # Step 2: Backfill existing rows with generated keys (for audit trail)
    # Format: transaction_type_semester_id_user_or_license_id
    # Note: Either user_id or user_license_id is set (check constraint)
    op.execute("""
        UPDATE credit_transactions
        SET idempotency_key = transaction_type || '_' ||
                              COALESCE(semester_id::text, 'null') || '_' ||
                              COALESCE(user_id::text, user_license_id::text, 'null') || '_' ||
                              COALESCE(enrollment_id::text, 'null') || '_' ||
                              id::text
        WHERE idempotency_key IS NULL;
    """)

    # Step 3: Make column NOT NULL
    op.alter_column('credit_transactions', 'idempotency_key', nullable=False)

    # Step 4: Add unique constraint
    op.create_unique_constraint(
        'uq_credit_transactions_idempotency_key',
        'credit_transactions',
        ['idempotency_key']
    )

    # Step 5: Add index for performance
    op.create_index(
        'ix_credit_transactions_idempotency_key',
        'credit_transactions',
        ['idempotency_key']
    )


def downgrade() -> None:
    """Remove idempotency_key column and constraints"""
    op.drop_index('ix_credit_transactions_idempotency_key', table_name='credit_transactions')
    op.drop_constraint('uq_credit_transactions_idempotency_key', 'credit_transactions', type_='unique')
    op.drop_column('credit_transactions', 'idempotency_key')