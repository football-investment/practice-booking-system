"""add_country_code_and_location_code_to_locations

Revision ID: 69e0fefaea60
Revises: 4bdfdfb13175
Create Date: 2026-01-13 17:24:53.371011

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '69e0fefaea60'
down_revision = '4bdfdfb13175'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add country_code column (2-letter ISO code)
    op.add_column('locations', sa.Column('country_code', sa.String(length=2), nullable=True))

    # Add location_code column (unique identifier like BDPST)
    op.add_column('locations', sa.Column('location_code', sa.String(length=10), nullable=True))

    # Create unique index on location_code
    op.create_index('ix_locations_location_code', 'locations', ['location_code'], unique=True)


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_locations_location_code', table_name='locations')

    # Drop columns
    op.drop_column('locations', 'location_code')
    op.drop_column('locations', 'country_code')