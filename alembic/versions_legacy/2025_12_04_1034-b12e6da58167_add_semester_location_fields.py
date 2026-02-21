"""add_semester_location_fields

Revision ID: b12e6da58167
Revises: f9b40d8e300b
Create Date: 2025-12-04 10:34:11.812339

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b12e6da58167'
down_revision = 'f9b40d8e300b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add location fields to semesters table
    op.add_column('semesters', sa.Column('location_city', sa.String(length=100), nullable=True,
                                         comment="City where semester takes place (e.g., 'Budapest', 'Debrecen')"))
    op.add_column('semesters', sa.Column('location_venue', sa.String(length=200), nullable=True,
                                         comment="Venue/campus name (e.g., 'Buda Campus', 'Pest Campus')"))
    op.add_column('semesters', sa.Column('location_address', sa.String(length=500), nullable=True,
                                         comment="Full address of the primary location"))


def downgrade() -> None:
    # Remove location fields from semesters table
    op.drop_column('semesters', 'location_address')
    op.drop_column('semesters', 'location_venue')
    op.drop_column('semesters', 'location_city')