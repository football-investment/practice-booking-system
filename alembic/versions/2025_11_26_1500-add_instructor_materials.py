"""add instructor materials to sessions

Revision ID: add_instructor_materials
Revises: (latest revision)
Create Date: 2025-11-26 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_instructor_materials'
down_revision = 'a1b2c3d4e5f6'  # Points to previous head
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to sessions table for instructor materials
    op.add_column('sessions', sa.Column('session_id_code', sa.String(50), nullable=True))
    op.add_column('sessions', sa.Column('module_number', sa.Integer, nullable=True))
    op.add_column('sessions', sa.Column('module_name', sa.String(200), nullable=True))
    op.add_column('sessions', sa.Column('session_number', sa.Integer, nullable=True))
    op.add_column('sessions', sa.Column('duration_minutes', sa.Integer, nullable=True))

    # Location details
    op.add_column('sessions', sa.Column('location_type', sa.String(20), nullable=True))  # physical, online, hybrid
    op.add_column('sessions', sa.Column('location_city', sa.String(100), nullable=True))
    op.add_column('sessions', sa.Column('location_venue', sa.String(200), nullable=True))
    op.add_column('sessions', sa.Column('location_address', sa.Text, nullable=True))

    # Instructor information
    op.add_column('sessions', sa.Column('instructor_role', sa.String(50), nullable=True))  # facilitator, mentor, etc.
    op.add_column('sessions', sa.Column('instructor_permissions', sa.String(50), nullable=True))  # read_only, etc.

    # Content fields
    op.add_column('sessions', sa.Column('student_description', sa.Text, nullable=True))  # Markdown for students
    op.add_column('sessions', sa.Column('instructor_materials', postgresql.JSONB(astext_type=sa.Text()), nullable=True))  # Full instructor guide as JSON

    # Create index on session_id_code for faster lookups
    op.create_index('ix_sessions_session_id_code', 'sessions', ['session_id_code'])


def downgrade():
    op.drop_index('ix_sessions_session_id_code', table_name='sessions')

    op.drop_column('sessions', 'instructor_materials')
    op.drop_column('sessions', 'student_description')
    op.drop_column('sessions', 'instructor_permissions')
    op.drop_column('sessions', 'instructor_role')
    op.drop_column('sessions', 'location_address')
    op.drop_column('sessions', 'location_venue')
    op.drop_column('sessions', 'location_city')
    op.drop_column('sessions', 'location_type')
    op.drop_column('sessions', 'duration_minutes')
    op.drop_column('sessions', 'session_number')
    op.drop_column('sessions', 'module_name')
    op.drop_column('sessions', 'module_number')
    op.drop_column('sessions', 'session_id_code')
