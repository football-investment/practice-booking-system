"""Fix INTERNSHIP level count - DB is source of truth (3 levels)

Revision ID: fix_internship_levels
Revises: unique_progress_constraint
Create Date: 2025-10-25 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_internship_levels'
down_revision = 'unique_progress_constraint'
branch_labels = None
depends_on = None


def upgrade():
    """
    P0 CRITICAL FIX: INTERNSHIP conflict resolution.

    Decision: DB has 3 levels, Helper claims 5. We make DB the source of truth.
    The migration seed created 3 levels (Junior, Mid, Senior).

    This migration:
    1. Confirms max_levels in specializations table = 3
    2. Documents the decision
    3. Helper code will be refactored to use DB dynamically

    No data changes needed - DB already has correct 3 levels.
    """

    # Update specializations table to ensure max_levels = 3 for INTERNSHIP
    op.execute("""
        UPDATE specializations
        SET max_levels = 3
        WHERE id = 'INTERNSHIP';
    """)

    # Add comment for clarity
    op.execute("""
        COMMENT ON TABLE internship_levels IS
        'Startup Spirit Internship - 3 levels (Junior, Mid-level, Senior).
         Helper code MUST query DB dynamically, NOT use hardcoded max_levels=5.';
    """)


def downgrade():
    """No downgrade - this is a documentation/clarification migration"""
    pass
