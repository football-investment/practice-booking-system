"""add INSTRUCTOR_CONFIRMED to assignment type constraint

Revision ID: add_instructor_confirmed
Revises: 69e0fefaea60
Create Date: 2026-01-13 20:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_instructor_confirmed'
down_revision = '69e0fefaea60'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add INSTRUCTOR_CONFIRMED status to the valid_assignment_type_instructor constraint.

    This status is used when:
    - OPEN_ASSIGNMENT: Admin directly assigns instructor and instructor accepts
    - APPLICATION_BASED: Admin approves instructor's application

    Both workflows result in INSTRUCTOR_CONFIRMED status before admin opens enrollment.
    """
    # Drop old constraint
    op.drop_constraint('valid_assignment_type_instructor', 'semesters', type_='check')

    # Create new constraint with INSTRUCTOR_CONFIRMED added
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
    """Revert to constraint without INSTRUCTOR_CONFIRMED"""
    op.drop_constraint('valid_assignment_type_instructor', 'semesters', type_='check')

    # Restore old constraint (without INSTRUCTOR_CONFIRMED)
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
