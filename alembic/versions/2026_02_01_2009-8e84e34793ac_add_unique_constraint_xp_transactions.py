"""add_unique_constraint_xp_transactions

Revision ID: 8e84e34793ac
Revises: 69606094ea87
Create Date: 2026-02-01 20:09:59.864294

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8e84e34793ac'
down_revision = '69606094ea87'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add unique constraint to xp_transactions table.

    Prevents DUAL PATH bug where multiple services write XP transactions
    for the same semester, creating duplicate XP awards.

    Business Invariant: One XP transaction per (user, semester_id, transaction_type).
    Example: Tournament 123 can only award "TOURNAMENT_REWARD" XP to User 5 ONCE.

    Note: xp_transactions uses semester_id (not source_type/source_id) to track source.
    """
    # Step 1: Delete existing duplicates (keep lowest id for each unique key)
    op.execute("""
        DELETE FROM xp_transactions a
        USING xp_transactions b
        WHERE a.id > b.id
        AND a.user_id = b.user_id
        AND COALESCE(a.semester_id, -1) = COALESCE(b.semester_id, -1)
        AND a.transaction_type = b.transaction_type;
    """)

    # Step 2: Add unique constraint
    op.create_unique_constraint(
        'uq_xp_transactions_user_semester_type',
        'xp_transactions',
        ['user_id', 'semester_id', 'transaction_type']
    )


def downgrade() -> None:
    """Remove unique constraint"""
    op.drop_constraint(
        'uq_xp_transactions_user_semester_type',
        'xp_transactions',
        type_='unique'
    )