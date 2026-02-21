"""add age_category to semester_enrollments

Revision ID: 7a8b9c0d1e2f
Revises: 03be2a3405e3
Create Date: 2025-12-28 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8810b2f3eea5'
down_revision = '03be2a3405e3'
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns already exist (idempotent migration)
    from sqlalchemy import inspect
    from sqlalchemy.engine import reflection

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('semester_enrollments')]

    # Add age_category column if it doesn't exist
    if 'age_category' not in existing_columns:
        op.add_column('semester_enrollments',
            sa.Column('age_category', sa.String(20), nullable=True,
                      comment="Age category at enrollment time (PRE/YOUTH/AMATEUR/PRO)"))

    # Add instructor_overridden flag if it doesn't exist
    if 'age_category_overridden' not in existing_columns:
        op.add_column('semester_enrollments',
            sa.Column('age_category_overridden', sa.Boolean, server_default='false', nullable=False,
                      comment="True if instructor manually changed age category"))

    # Add override timestamp if it doesn't exist
    if 'age_category_overridden_at' not in existing_columns:
        op.add_column('semester_enrollments',
            sa.Column('age_category_overridden_at', sa.DateTime, nullable=True,
                      comment="When age category was overridden by instructor"))

    # Add override author if it doesn't exist
    if 'age_category_overridden_by' not in existing_columns:
        op.add_column('semester_enrollments',
            sa.Column('age_category_overridden_by', sa.Integer,
                      sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True,
                      comment="Instructor who overrode the age category"))

    # Create index on age_category for faster queries (if it doesn't exist)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('semester_enrollments')]
    if 'ix_semester_enrollments_age_category' not in existing_indexes:
        op.create_index('ix_semester_enrollments_age_category', 'semester_enrollments', ['age_category'])


def downgrade():
    # Drop index first
    op.drop_index('ix_semester_enrollments_age_category', table_name='semester_enrollments')

    # Drop columns in reverse order
    op.drop_column('semester_enrollments', 'age_category_overridden_by')
    op.drop_column('semester_enrollments', 'age_category_overridden_at')
    op.drop_column('semester_enrollments', 'age_category_overridden')
    op.drop_column('semester_enrollments', 'age_category')
