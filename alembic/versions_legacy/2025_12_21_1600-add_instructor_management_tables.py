"""add instructor management tables

Revision ID: 7a8b9c0d1e2f
Revises: f9b40d8e300b
Create Date: 2025-12-21 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7a8b9c0d1e2f'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    """
    Instructor Management System Tables

    Creates:
    1. location_master_instructors - Master instructor contracts (one per location)
    2. instructor_positions - Job postings by master instructors
    3. position_applications - Instructor applications to positions
    4. instructor_assignments - Active instructor assignments (supports co-instructors)

    Modifies:
    - instructor_assignment_requests - Adds location_id column
    """

    # ========================================================================
    # 1. Add location_id to instructor_assignment_requests
    # ========================================================================

    op.add_column('instructor_assignment_requests',
        sa.Column('location_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_instructor_assignment_requests_location',
        'instructor_assignment_requests',
        'locations',
        ['location_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index(
        'idx_instructor_requests_location',
        'instructor_assignment_requests',
        ['location_id']
    )

    # ========================================================================
    # 2. Create location_master_instructors table
    # ========================================================================

    op.create_table(
        'location_master_instructors',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('location_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('instructor_id', sa.Integer(), nullable=False),
        sa.Column('contract_start', sa.Date(), nullable=False),
        sa.Column('contract_end', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('terminated_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Unique constraint: only one active master per location
    op.create_index(
        'idx_one_active_master_per_location',
        'location_master_instructors',
        ['location_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true')
    )

    op.create_index(
        'idx_master_instructors_instructor',
        'location_master_instructors',
        ['instructor_id']
    )

    # ========================================================================
    # 3. Create instructor_positions table (job postings)
    # ========================================================================

    op.create_table(
        'instructor_positions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('posted_by', sa.Integer(), nullable=False),
        sa.Column('specialization_type', sa.String(50), nullable=False),
        sa.Column('age_group', sa.String(20), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('time_period_start', sa.String(10), nullable=False),
        sa.Column('time_period_end', sa.String(10), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=5),
        sa.Column('status', sa.String(20), nullable=False, default='OPEN'),
        sa.Column('application_deadline', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),

        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['posted_by'], ['users.id'], ondelete='CASCADE'),
    )

    op.create_index('idx_positions_location', 'instructor_positions', ['location_id'])
    op.create_index('idx_positions_status', 'instructor_positions', ['status'])
    op.create_index('idx_positions_posted_by', 'instructor_positions', ['posted_by'])
    op.create_index('idx_positions_deadline', 'instructor_positions', ['application_deadline'])

    # ========================================================================
    # 4. Create position_applications table
    # ========================================================================

    op.create_table(
        'position_applications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('applicant_id', sa.Integer(), nullable=False),
        sa.Column('application_message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='PENDING'),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),

        sa.ForeignKeyConstraint(['position_id'], ['instructor_positions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], ondelete='CASCADE'),

        # One application per instructor per position
        sa.UniqueConstraint('position_id', 'applicant_id', name='uq_position_applicant')
    )

    op.create_index('idx_applications_position', 'position_applications', ['position_id'])
    op.create_index('idx_applications_applicant', 'position_applications', ['applicant_id'])
    op.create_index('idx_applications_status', 'position_applications', ['status'])

    # ========================================================================
    # 5. Create instructor_assignments table (active assignments)
    # ========================================================================

    op.create_table(
        'instructor_assignments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('instructor_id', sa.Integer(), nullable=False),
        sa.Column('specialization_type', sa.String(50), nullable=False),
        sa.Column('age_group', sa.String(20), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('time_period_start', sa.String(10), nullable=False),
        sa.Column('time_period_end', sa.String(10), nullable=False),
        sa.Column('is_master', sa.Boolean(), nullable=False, default=False),
        sa.Column('assigned_by', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),

        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('idx_assignments_location_year', 'instructor_assignments', ['location_id', 'year'])
    op.create_index('idx_assignments_instructor', 'instructor_assignments', ['instructor_id'])
    op.create_index('idx_assignments_active', 'instructor_assignments', ['is_active'])
    op.create_index('idx_assignments_spec_age', 'instructor_assignments', ['specialization_type', 'age_group'])


def downgrade():
    """Rollback instructor management tables"""

    # Drop tables in reverse order
    op.drop_table('instructor_assignments')
    op.drop_table('position_applications')
    op.drop_table('instructor_positions')
    op.drop_table('location_master_instructors')

    # Remove location_id from instructor_assignment_requests
    op.drop_index('idx_instructor_requests_location', 'instructor_assignment_requests')
    op.drop_constraint('fk_instructor_assignment_requests_location', 'instructor_assignment_requests', type_='foreignkey')
    op.drop_column('instructor_assignment_requests', 'location_id')
