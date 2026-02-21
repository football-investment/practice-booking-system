"""add session group assignments

Revision ID: 2025_12_25_2000
Revises: 2025_12_23_1900
Create Date: 2025-12-25 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_12_25_2000'
down_revision = '2025_12_23_1900'
branch_labels = None
depends_on = None


def upgrade():
    # Create session_group_assignments table
    # This stores the DYNAMIC group assignments created at session start
    op.create_table(
        'session_group_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('group_number', sa.Integer(), nullable=False,
                  comment='Group number within session (1, 2, 3, 4...)'),
        sa.Column('instructor_id', sa.Integer(), nullable=False,
                  comment='Instructor assigned to this group'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False,
                  comment='Head coach who created the group assignment'),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),

        # Ensure unique group number within session
        sa.UniqueConstraint('session_id', 'group_number', name='uq_session_group_number')
    )

    # Create session_group_students table
    # This stores which students are assigned to which group AT SESSION START
    op.create_table(
        'session_group_students',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_group_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_group_id'], ['session_group_assignments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),

        # One student can only be in one group per session
        sa.UniqueConstraint('session_group_id', 'student_id', name='uq_session_group_student')
    )

    # Add index for fast lookups
    op.create_index('idx_session_groups_session', 'session_group_assignments', ['session_id'])
    op.create_index('idx_session_group_students_group', 'session_group_students', ['session_group_id'])


def downgrade():
    op.drop_index('idx_session_group_students_group')
    op.drop_index('idx_session_groups_session')
    op.drop_table('session_group_students')
    op.drop_table('session_group_assignments')
