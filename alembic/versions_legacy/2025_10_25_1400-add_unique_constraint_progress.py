"""Add unique constraint to specialization_progress

Revision ID: unique_progress_constraint
Revises: spec_level_system
Create Date: 2025-10-25 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'unique_progress_constraint'
down_revision = 'fc73d1aca3f3'
branch_labels = None
depends_on = None


def upgrade():
    """
    P0 CRITICAL FIX: Add UniqueConstraint to prevent duplicate progress records.

    Problem: Multiple progress records for same (student_id, specialization_id)
    causes data integrity issues and unpredictable behavior.

    This ensures each student has exactly ONE progress record per specialization.
    """

    # Clean up any existing duplicates before adding constraint
    op.execute("""
        -- Delete duplicate records, keeping only the one with highest current_level
        DELETE FROM specialization_progress
        WHERE id NOT IN (
            SELECT DISTINCT ON (student_id, specialization_id)
                id
            FROM specialization_progress
            ORDER BY student_id, specialization_id, current_level DESC, updated_at DESC
        );
    """)

    # Add unique constraint
    op.create_unique_constraint(
        "uq_specialization_progress_user_spec",
        "specialization_progress",
        ["student_id", "specialization_id"]
    )


def downgrade():
    """Remove unique constraint"""
    op.drop_constraint(
        "uq_specialization_progress_user_spec",
        "specialization_progress",
        type_="unique"
    )
