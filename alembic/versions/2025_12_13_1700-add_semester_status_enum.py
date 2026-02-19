"""Add semester status enum for lifecycle management

Revision ID: add_semester_status
Revises: ff330f866c45
Create Date: 2025-12-13 17:00:00

Changes:
- Add semester_status ENUM type with lifecycle phases
- Add status column to semesters table (default: DRAFT)
- Keep is_active for backward compatibility (will be deprecated)

Semester Lifecycle:
1. DRAFT - Admin created, no instructor, no sessions
2. SEEKING_INSTRUCTOR - Admin looking for instructor
3. INSTRUCTOR_ASSIGNED - Has instructor, no sessions yet
4. READY_FOR_ENROLLMENT - Has instructor + sessions, students can enroll
5. ONGOING - Past enrollment deadline, classes in progress
6. COMPLETED - All sessions finished
7. CANCELLED - Admin cancelled
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_semester_status'
down_revision = 'g2h3i4j5k6l7'
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM type for semester status
    semester_status_enum = sa.Enum(
        'DRAFT',
        'SEEKING_INSTRUCTOR',
        'INSTRUCTOR_ASSIGNED',
        'READY_FOR_ENROLLMENT',
        'ONGOING',
        'COMPLETED',
        'CANCELLED',
        name='semester_status'
    )
    semester_status_enum.create(op.get_bind(), checkfirst=True)

    # Add status column to semesters table
    op.add_column('semesters',
        sa.Column('status',
                  sa.Enum(
                      'DRAFT',
                      'SEEKING_INSTRUCTOR',
                      'INSTRUCTOR_ASSIGNED',
                      'READY_FOR_ENROLLMENT',
                      'ONGOING',
                      'COMPLETED',
                      'CANCELLED',
                      name='semester_status'
                  ),
                  nullable=False,
                  server_default='DRAFT',
                  comment='Current lifecycle phase of the semester'
        )
    )

    # Migrate existing data based on is_active flag
    # If is_active=true and has sessions -> READY_FOR_ENROLLMENT
    # If is_active=true and no sessions -> DRAFT
    # If is_active=false -> CANCELLED
    op.execute("""
        UPDATE semesters
        SET status = CASE
            WHEN is_active = true AND EXISTS (
                SELECT 1 FROM sessions WHERE sessions.semester_id = semesters.id
            ) THEN 'READY_FOR_ENROLLMENT'::semester_status
            WHEN is_active = true THEN 'DRAFT'::semester_status
            ELSE 'CANCELLED'::semester_status
        END
    """)

    # Add index for status queries
    op.create_index('ix_semesters_status', 'semesters', ['status'])


def downgrade():
    # Remove index
    op.drop_index('ix_semesters_status', 'semesters')

    # Remove column
    op.drop_column('semesters', 'status')

    # Drop ENUM type
    semester_status_enum = sa.Enum(
        'DRAFT',
        'SEEKING_INSTRUCTOR',
        'INSTRUCTOR_ASSIGNED',
        'READY_FOR_ENROLLMENT',
        'ONGOING',
        'COMPLETED',
        'CANCELLED',
        name='semester_status'
    )
    semester_status_enum.drop(op.get_bind(), checkfirst=True)
