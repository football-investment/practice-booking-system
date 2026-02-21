"""fix assignment type instructor constraint

Revision ID: 71f227317750
Revises: 78502c79192c
Create Date: 2026-01-12 17:33:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '71f227317750'
down_revision = '78502c79192c'
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix the valid_assignment_type_instructor constraint.

    OLD LOGIC (BROKEN):
    - OPEN_ASSIGNMENT REQUIRES instructor_id NOT NULL at creation

    NEW LOGIC (CORRECT):
    - OPEN_ASSIGNMENT: instructor_id can be NULL at creation (SEEKING_INSTRUCTOR status)
    - APPLICATION_BASED: instructor_id can be NULL until admin selects
    - Both: instructor_id must be NOT NULL when status = READY_FOR_ENROLLMENT or later
    """
    # Drop old constraint
    op.drop_constraint('valid_assignment_type_instructor', 'semesters', type_='check')

    # Create new constraint
    # Logic:
    # - If assignment_type IS NULL: allow anything (backward compatibility)
    # - If assignment_type = 'OPEN_ASSIGNMENT':
    #     - Allow instructor_id = NULL when status = 'SEEKING_INSTRUCTOR'
    #     - Require instructor_id NOT NULL for other statuses
    # - If assignment_type = 'APPLICATION_BASED':
    #     - Allow instructor_id = NULL when status = 'SEEKING_INSTRUCTOR' or 'PENDING_INSTRUCTOR_ACCEPTANCE'
    #     - Require instructor_id NOT NULL for other statuses
    op.create_check_constraint(
        'valid_assignment_type_instructor',
        'semesters',
        """
        (assignment_type IS NULL)
        OR
        (
            assignment_type = 'OPEN_ASSIGNMENT'
            AND (
                (tournament_status = 'SEEKING_INSTRUCTOR' AND master_instructor_id IS NULL)
                OR
                (tournament_status IN ('PENDING_INSTRUCTOR_ACCEPTANCE', 'READY_FOR_ENROLLMENT', 'ENROLLMENT_OPEN', 'IN_PROGRESS', 'ENROLLMENT_CLOSED', 'COMPLETED') AND master_instructor_id IS NOT NULL)
            )
        )
        OR
        (
            assignment_type = 'APPLICATION_BASED'
            AND (
                (tournament_status IN ('SEEKING_INSTRUCTOR', 'PENDING_INSTRUCTOR_ACCEPTANCE') AND (master_instructor_id IS NULL OR master_instructor_id IS NOT NULL))
                OR
                (tournament_status IN ('READY_FOR_ENROLLMENT', 'ENROLLMENT_OPEN', 'IN_PROGRESS', 'ENROLLMENT_CLOSED', 'COMPLETED') AND master_instructor_id IS NOT NULL)
            )
        )
        """
    )


def downgrade():
    """Revert to old constraint"""
    op.drop_constraint('valid_assignment_type_instructor', 'semesters', type_='check')

    # Restore old constraint (broken logic)
    op.create_check_constraint(
        'valid_assignment_type_instructor',
        'semesters',
        """
        (assignment_type IS NULL)
        OR
        (assignment_type = 'OPEN_ASSIGNMENT' AND master_instructor_id IS NOT NULL)
        OR
        (assignment_type = 'APPLICATION_BASED' AND (master_instructor_id IS NULL OR tournament_status IN ('PENDING_INSTRUCTOR_ACCEPTANCE', 'READY_FOR_ENROLLMENT', 'ENROLLMENT_OPEN', 'ENROLLMENT_CLOSED', 'COMPLETED')))
        """
    )
