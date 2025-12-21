"""create attendance table

Revision ID: a1b2c3d4e5f6
Revises: f00c64f4c615
Create Date: 2025-11-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f00c64f4c615'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'attendance',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PRESENT'),
        sa.Column('marked_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('marked_by', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['marked_by'], ['users.id']),
        sa.UniqueConstraint('session_id', 'student_id', name='uq_attendance_session_student')
    )
    op.create_index('ix_attendance_session_id', 'attendance', ['session_id'])
    op.create_index('ix_attendance_student_id', 'attendance', ['student_id'])


def downgrade():
    op.drop_index('ix_attendance_student_id', table_name='attendance')
    op.drop_index('ix_attendance_session_id', table_name='attendance')
    op.drop_table('attendance')
