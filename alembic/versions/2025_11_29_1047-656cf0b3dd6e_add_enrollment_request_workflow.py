"""add_enrollment_request_workflow

Revision ID: 656cf0b3dd6e
Revises: 65966697301f
Create Date: 2025-11-29 10:47:27.484529

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '656cf0b3dd6e'
down_revision = '65966697301f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for enrollment status
    enrollment_status_enum = sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'WITHDRAWN', name='enrollmentstatus')
    enrollment_status_enum.create(op.get_bind(), checkfirst=True)

    # Add new columns to semester_enrollments table
    op.add_column('semester_enrollments', sa.Column('request_status', enrollment_status_enum, nullable=False, server_default='PENDING'))
    op.add_column('semester_enrollments', sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')))
    op.add_column('semester_enrollments', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('semester_enrollments', sa.Column('approved_by', sa.Integer(), nullable=True))
    op.add_column('semester_enrollments', sa.Column('rejection_reason', sa.String(), nullable=True))

    # Add foreign key constraint for approved_by
    op.create_foreign_key('fk_semester_enrollments_approved_by', 'semester_enrollments', 'users', ['approved_by'], ['id'], ondelete='SET NULL')

    # Add index for request_status
    op.create_index('ix_semester_enrollments_request_status', 'semester_enrollments', ['request_status'])

    # Update existing enrollments to APPROVED status (backward compatibility)
    op.execute("UPDATE semester_enrollments SET request_status = 'APPROVED' WHERE is_active = true")

    # Change is_active default to False (new enrollments start inactive until approved)
    op.alter_column('semester_enrollments', 'is_active', server_default=sa.text('false'))


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_semester_enrollments_request_status', 'semester_enrollments')

    # Remove foreign key
    op.drop_constraint('fk_semester_enrollments_approved_by', 'semester_enrollments', type_='foreignkey')

    # Remove columns
    op.drop_column('semester_enrollments', 'rejection_reason')
    op.drop_column('semester_enrollments', 'approved_by')
    op.drop_column('semester_enrollments', 'approved_at')
    op.drop_column('semester_enrollments', 'requested_at')
    op.drop_column('semester_enrollments', 'request_status')

    # Drop enum type
    sa.Enum(name='enrollmentstatus').drop(op.get_bind(), checkfirst=True)

    # Restore is_active default
    op.alter_column('semester_enrollments', 'is_active', server_default=sa.text('true'))