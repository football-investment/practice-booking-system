"""drop_semester_is_active

Drop the deprecated Semester.is_active Boolean column.
All query sites now use Semester.status != SemesterStatus.CANCELLED instead.

Revision ID: 2026_03_12_1000
Revises: 2026_03_09_1500
Create Date: 2026-03-12 10:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2026_03_12_1000'
down_revision = '2026_03_09_1500'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('semesters', 'is_active')


def downgrade() -> None:
    op.add_column(
        'semesters',
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true'),
                  comment='DEPRECATED: Use status field instead. Restored by downgrade.')
    )
    # Restore values: not CANCELLED → True, CANCELLED → False
    op.execute(
        "UPDATE semesters SET is_active = (status != 'CANCELLED')"
    )
