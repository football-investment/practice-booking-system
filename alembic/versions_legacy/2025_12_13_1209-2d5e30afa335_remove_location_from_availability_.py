"""remove_location_from_availability_windows

Revision ID: 2d5e30afa335
Revises: 5f7a8b9c0d1e
Create Date: 2025-12-13 12:09:01.498165

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d5e30afa335'
down_revision = '5f7a8b9c0d1e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop location_city column from instructor_availability_windows
    op.drop_column('instructor_availability_windows', 'location_city')


def downgrade() -> None:
    # Re-add location_city column if we need to rollback
    op.add_column('instructor_availability_windows',
        sa.Column('location_city', sa.String(length=100), nullable=True))