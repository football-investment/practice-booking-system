"""add_master_instructor_to_semester

Revision ID: cf7bf280ac2a
Revises: 4bb3b055b551
Create Date: 2025-12-01 22:03:42.057425

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf7bf280ac2a'
down_revision = '4bb3b055b551'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add master_instructor_id column to semesters table
    op.add_column('semesters',
                  sa.Column('master_instructor_id', sa.Integer(), nullable=True,
                           comment='Master instructor who approves enrollment requests for this semester'))
    op.create_foreign_key('fk_semesters_master_instructor',
                         'semesters', 'users',
                         ['master_instructor_id'], ['id'],
                         ondelete='SET NULL')

    # Create semester_instructors many-to-many table
    op.create_table('semester_instructors',
        sa.Column('semester_id', sa.Integer(), nullable=False),
        sa.Column('instructor_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['semester_id'], ['semesters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instructor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('semester_id', 'instructor_id')
    )


def downgrade() -> None:
    # Drop semester_instructors table
    op.drop_table('semester_instructors')

    # Drop master_instructor_id column
    op.drop_constraint('fk_semesters_master_instructor', 'semesters', type_='foreignkey')
    op.drop_column('semesters', 'master_instructor_id')