"""create_instructor_assignment_system

Revision ID: 5f7a8b9c0d1e
Revises: 4da8caa1e3d0
Create Date: 2025-12-13 13:00:00.000000

New Demand-Driven Instructor Assignment System:

1. InstructorAvailabilityWindow: Simplified availability (time period + location only)
2. InstructorAssignmentRequest: Admin sends requests to instructors for specific semesters

Workflow:
- Instructor: "I'm available Q3 2026 in Budapest"
- Admin: Creates PRE semester Q3 Budapest
- Admin: Sends request to instructor
- Instructor: Accepts/Declines
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5f7a8b9c0d1e'
down_revision = '4da8caa1e3d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create AssignmentRequestStatus enum
    assignment_status_enum = postgresql.ENUM(
        'PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED', 'EXPIRED',
        name='assignmentrequeststatus',
        create_type=False  # Don't auto-create, we'll handle it manually
    )

    # Check if enum exists, if not create it
    connection = op.get_bind()
    result = connection.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'assignmentrequeststatus'"
    )).fetchone()

    if not result:
        assignment_status_enum.create(connection, checkfirst=True)

    # Create instructor_availability_windows table
    op.create_table(
        'instructor_availability_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instructor_id', sa.Integer(), nullable=False, comment='Instructor setting availability'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Year (e.g., 2026)'),
        sa.Column('time_period', sa.String(length=10), nullable=False, comment='Q1, Q2, Q3, Q4 or M01-M12'),
        sa.Column('location_city', sa.String(length=100), nullable=False, comment='City where instructor can work'),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true', comment='True if instructor is available'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True, comment='Optional notes from instructor'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign key
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes for availability_windows
    op.create_index('ix_avail_window_instructor', 'instructor_availability_windows', ['instructor_id'])
    op.create_index('ix_avail_window_year', 'instructor_availability_windows', ['year'])
    op.create_index('ix_avail_window_period', 'instructor_availability_windows', ['time_period'])
    op.create_index('ix_avail_window_location', 'instructor_availability_windows', ['location_city'])

    # Create instructor_assignment_requests table
    op.create_table(
        'instructor_assignment_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semester_id', sa.Integer(), nullable=False, comment='Semester needing an instructor'),
        sa.Column('instructor_id', sa.Integer(), nullable=False, comment='Instructor receiving the request'),
        sa.Column('requested_by', sa.Integer(), nullable=True, comment='Admin who sent the request'),
        sa.Column('status', assignment_status_enum, nullable=False, server_default='PENDING',
                 comment='PENDING, ACCEPTED, DECLINED, CANCELLED, EXPIRED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True, comment='When instructor responded'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Request expiration'),
        sa.Column('request_message', sa.Text(), nullable=True, comment='Message from admin'),
        sa.Column('response_message', sa.Text(), nullable=True, comment='Message from instructor'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0', comment='Priority 0-10'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for assignment_requests
    op.create_index('ix_assign_req_semester', 'instructor_assignment_requests', ['semester_id'])
    op.create_index('ix_assign_req_instructor', 'instructor_assignment_requests', ['instructor_id'])
    op.create_index('ix_assign_req_status', 'instructor_assignment_requests', ['status'])
    op.create_index('ix_assign_req_created', 'instructor_assignment_requests', ['created_at'])


def downgrade() -> None:
    # Drop indexes for assignment_requests
    op.drop_index('ix_assign_req_created', table_name='instructor_assignment_requests')
    op.drop_index('ix_assign_req_status', table_name='instructor_assignment_requests')
    op.drop_index('ix_assign_req_instructor', table_name='instructor_assignment_requests')
    op.drop_index('ix_assign_req_semester', table_name='instructor_assignment_requests')

    # Drop assignment_requests table
    op.drop_table('instructor_assignment_requests')

    # Drop indexes for availability_windows
    op.drop_index('ix_avail_window_location', table_name='instructor_availability_windows')
    op.drop_index('ix_avail_window_period', table_name='instructor_availability_windows')
    op.drop_index('ix_avail_window_year', table_name='instructor_availability_windows')
    op.drop_index('ix_avail_window_instructor', table_name='instructor_availability_windows')

    # Drop availability_windows table
    op.drop_table('instructor_availability_windows')

    # Drop enum
    assignment_status_enum = postgresql.ENUM(
        'PENDING', 'ACCEPTED', 'DECLINED', 'CANCELLED', 'EXPIRED',
        name='assignmentrequeststatus'
    )
    assignment_status_enum.drop(op.get_bind())
