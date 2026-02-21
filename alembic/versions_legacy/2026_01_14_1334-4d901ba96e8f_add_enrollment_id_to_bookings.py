"""add_enrollment_id_to_bookings

Revision ID: 4d901ba96e8f
Revises: add_instructor_confirmed
Create Date: 2026-01-14 13:34:46.016093

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d901ba96e8f'
down_revision = 'add_instructor_confirmed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add enrollment_id column to bookings table
    op.add_column('bookings', sa.Column('enrollment_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_bookings_enrollment_id'), 'bookings', ['enrollment_id'], unique=False)
    op.create_foreign_key('fk_bookings_enrollment_id', 'bookings', 'semester_enrollments', ['enrollment_id'], ['id'])


def downgrade() -> None:
    # Remove enrollment_id column from bookings table
    op.drop_constraint('fk_bookings_enrollment_id', 'bookings', type_='foreignkey')
    op.drop_index(op.f('ix_bookings_enrollment_id'), table_name='bookings')
    op.drop_column('bookings', 'enrollment_id')